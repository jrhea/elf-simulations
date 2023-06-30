"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing"""
from __future__ import annotations

import json
import logging
import os
import time

from eth_typing import URI, BlockNumber
from web3 import Web3

from elfpy.data import contract_interface, postgres
from elfpy.data.pool_info import PoolInfo
from elfpy.utils import outputs as output_utils

# pylint: disable=too-many-arguments


def main(
    contracts_url: str,
    ethereum_node: URI | str,
    state_abi_file_path: str,
    transactions_abi_file_path: str,
    save_dir: str,
    start_block: int,
    lookback_block_limit: int,
    sleep_amount: int,
):
    """Main entry point for accessing contract & writing pool info"""
    # TODO: refactor this function, its waaay to big as indicated by these pylints
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # initialize the postgres session
    session = postgres.initialize_session()
    # get web3 provider
    web3: Web3 = contract_interface.initialize_web3_with_http_provider(ethereum_node, request_kwargs={"timeout": 60})
    # send a request to the local server to fetch the deployed contract addresses and
    # load the deployed Hyperdrive contract addresses from the server response
    state_hyperdrive_contract = contract_interface.get_hyperdrive_contract(state_abi_file_path, contracts_url, web3)
    transactions_hyperdrive_contract = contract_interface.get_hyperdrive_contract(
        transactions_abi_file_path, contracts_url, web3
    )
    # get pool config from hyperdrive contract
    config_file = os.path.join(save_dir, "hyperdrive_config.json")
    config_dict = contract_interface.get_hyperdrive_config(state_hyperdrive_contract)
    logging.info("Writing pool config.")
    with open(config_file, mode="w", encoding="UTF-8") as file:
        json.dump(config_dict, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
    # write the initial pool info
    block_number: BlockNumber = BlockNumber(start_block)
    latest_block_number = web3.eth.get_block_number()
    lookback_block_limit = BlockNumber(lookback_block_limit)
    if (latest_block_number - block_number) > lookback_block_limit:
        block_number = BlockNumber(latest_block_number - lookback_block_limit)
        logging.warning("Starting block is past lookback block limit, starting at block %s", block_number)

    pool_info: list[PoolInfo] = []
    pool_info_file = os.path.join(save_dir, "hyperdrive_pool_info.json")

    block_pool_info: PoolInfo = contract_interface.get_block_pool_info(web3, state_hyperdrive_contract, block_number)
    pool_info.append(block_pool_info)

    # save backfilled pool info to file
    with open(pool_info_file, mode="w", encoding="UTF-8") as file:
        json.dump(pool_info, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
    # save pool info to postgres
    postgres.add_pool_infos(pool_info, session)

    transaction_info = []
    transaction_info_file = os.path.join(save_dir, "hyperdrive_transactions.json")

    # monitor for new blocks & add pool info per block
    logging.info("Monitoring for pool info updates...")
    while True:
        latest_block_number = web3.eth.get_block_number()
        # if we are on a new block
        if latest_block_number > block_number:
            # Backfilling for blocks that need updating
            for block_int in range(block_number + 1, latest_block_number + 1):
                block_number: BlockNumber = BlockNumber(block_int)
                logging.info("Block %s", block_number)

                # Explicit check against loopback block limit
                if (latest_block_number - block_number) > lookback_block_limit:
                    logging.warning(
                        "Querying block_number %s out of %s, unable to keep up with chain block iteration",
                        block_number,
                        latest_block_number,
                    )
                    continue

                # get_block_pool_info crashes randomly with ValueError on some intermediate block,
                # keep trying until it returns
                while True:
                    try:
                        block_pool_info = contract_interface.get_block_pool_info(
                            web3, state_hyperdrive_contract, block_number
                        )
                        break
                    except ValueError:
                        logging.warning("Error in get_block_pool_info, retrying")
                        time.sleep(0.1)
                        continue

                if block_pool_info:
                    postgres.add_pool_infos([block_pool_info], session)
                    pool_info.append(block_pool_info)
                block_transactions = contract_interface.fetch_transactions_for_block(
                    web3, transactions_hyperdrive_contract, block_number
                )
                if block_transactions:
                    transaction_info.extend(block_transactions)
            # save pool info to file and postgres
            with open(pool_info_file, mode="w", encoding="UTF-8") as file:
                json.dump(pool_info, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
            # save transactions to file
            with open(transaction_info_file, mode="w", encoding="UTF-8") as file:
                json.dump(transaction_info, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
        time.sleep(sleep_amount)


if __name__ == "__main__":
    # setup constants
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    ETHEREUM_NODE = "http://localhost:8545"
    SAVE_DIR = ".logging"
    STATE_ABI_FILE_PATH = "./hyperdrive_solidity/.build/IHyperdrive.json"
    TRANSACTIONS_ABI_FILE_PATH = "./hyperdrive_solidity/.build/IHyperdrive.json"
    START_BLOCK = 6
    # Look back limit for backfilling
    LOOKBACK_BLOCK_LIMIT = 1000
    SLEEP_AMOUNT = 1
    output_utils.setup_logging(".logging/acquire_data.log", log_file_and_stdout=True)
    main(
        CONTRACTS_URL,
        ETHEREUM_NODE,
        STATE_ABI_FILE_PATH,
        TRANSACTIONS_ABI_FILE_PATH,
        SAVE_DIR,
        START_BLOCK,
        LOOKBACK_BLOCK_LIMIT,
        SLEEP_AMOUNT,
    )