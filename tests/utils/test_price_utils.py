"""
Testing for price utilities found in src/elfpy/utils/price.py
"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import unittest
import numpy as np

from elfpy.markets import Market
from elfpy.types import MarketState, StretchedTime
from elfpy.utils import price as price_utils
from elfpy.utils import sim_utils


class BasePriceTest(unittest.TestCase):
    """Unit tests for price utilities"""

    def run_calc_liquidity_test(self, pricing_model):
        """Unit tests for the pricing model calc_liquidity function

        Example check for the test:
            # test 1: 5M target_liquidity; 5% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            l = target_liquidity = 5_000_000
            r = target_apr = 0.05
            days = 182.5
            time_stretch = 3.09396 / (0.02789 * r * 100)
            t = days / 365
            T = t / time_stretch
            u = init_share_price = 1
            c = share_price = 1  # share price of the LP in the yield source; c = 1
            z = share_reserves = l / c
            y = bond_reserves = (z / 2) * (u * (1 + r * t) ** (1 / T) - c)
            p = ((2 * y + c * z) / (u * z)) ** (-T)  # spot price from reserves
            final_apr = (1 - p) / (p * t)
            total_liquidity = c * z
        """

        test_cases = [
            # test 1: 5M target_liquidity; 5% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity": 5_000_000,  # Targeting 5M liquidity
                "target_apr": 0.05,  # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months remaining; t = 0.50,
                    time_stretch=22.186877016851916,
                ),
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "expected_share_reserves": 5_000_000,  # target_liquidity / share_price
                "expected_bond_reserves": 4_978_218.90560554,
            },
            # test 2: 5M target_liquidity; 2% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity": 5_000_000,  # Targeting 5M liquidity
                "target_apr": 0.02,  # fixed rate APR you'd get from purchasing bonds; r = 0.02
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months remaining; t = 0.50
                    time_stretch=55.467192542129794,
                ),
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "expected_share_reserves": 5_000_000.0,  # target_liquidity / share_price
                "expected_bond_reserves": 5_039_264.014565533,
            },
            # test 3: 5M target_liquidity; 8% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity": 5_000_000,  # Targeting 5M liquidity
                "target_apr": 0.08,  # fixed rate APR you'd get from purchasing bonds; r = 0.08
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months remaining; t = 0.50
                    time_stretch=13.866798135532449,
                ),
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "expected_share_reserves": 5_000_000.0,
                "expected_bond_reserves": 4_918_835.884062026,
            },
            # test 4:  10M target_liquidity; 3% APR
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity": 10_000_000,  # Targeting 10M liquidity
                "target_apr": 0.03,  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months remaining; t = 0.25
                    time_stretch=36.97812836141987,
                ),
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "expected_share_reserves": 5_000_000.0,
                "expected_bond_reserves": 6_324_407.309278079,
            },
            # test 5:  10M target_liquidity; 5% APR
            #   9mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity": 10_000_000,  # Targeting 10M liquidity
                "target_apr": 0.03,  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "time_remaining": StretchedTime(
                    days=273.75,  # 9 months remaining; t = 0.75
                    time_stretch=36.97812836141987,
                ),
                "init_share_price": 1.3,  # original share price when pool started
                "share_price": 1.5,  # share price of the LP in the yield source
                "expected_share_reserves": 6666666.666666667,
                "expected_bond_reserves": 7979677.952016878,
            },
            # test 6: ERROR CASE: 0 TARGET LIQUIDITY -> ZeroDivisionError
            #   10M target_liquidity; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity": 0,  # ERROR CASE; Targeting 0 liquidity
                "target_apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months remaining; t = 0.25
                    time_stretch=36.97812836141986,
                ),
                "init_share_price": 1,  # original share price when pool started
                "share_price": 1,  # share price of the LP in the yield source
                "is_error_case": True,  # this test is supposed to fail
                "expected_result": ZeroDivisionError,
                "expected_share_reserves": ZeroDivisionError,  #
                "expected_bond_reserves": ZeroDivisionError,  #
            },
        ]
        # Loop through the test cases & pricing model
        for test_case in [test_cases[0]]:
            # Check if this test case is supposed to fail
            if "is_error_case" in test_case and test_case["is_error_case"]:
                # Check that test case throws the expected error
                with self.assertRaises(test_case["expected_result"]):
                    # share, bond
                    share_reserves, bond_reserves = price_utils.calc_liquidity(
                        target_liquidity=test_case["target_liquidity"],
                        target_apr=test_case["target_apr"],
                        market=Market(
                            market_state=MarketState(
                                init_share_price=test_case["init_share_price"],
                                share_price=test_case["share_price"],
                            ),
                            position_duration=test_case["time_remaining"],
                        ),
                        pricing_model=pricing_model,
                    )
            # If test was not supposed to fail, continue normal execution
            else:
                market = Market(
                    market_state=MarketState(
                        init_share_price=test_case["init_share_price"],
                        share_price=test_case["share_price"],
                    ),
                    position_duration=test_case["time_remaining"],
                )
                share_reserves, bond_reserves = price_utils.calc_liquidity(
                    target_liquidity=test_case["target_liquidity"],
                    target_apr=test_case["target_apr"],
                    market=market,
                    pricing_model=pricing_model,
                )
                np.testing.assert_almost_equal(
                    test_case["expected_share_reserves"],
                    share_reserves,
                    err_msg="unexpected share_reserves",
                )
                np.testing.assert_almost_equal(
                    test_case["expected_bond_reserves"],
                    bond_reserves,
                    err_msg="unexpected bond_reserves",
                )

    # ### Spot Price and APR ###

    def run_calc_apr_from_spot_price_test(self):
        """Unit tests for the calc_apr_from_spot_price function"""

        test_cases = [
            # test 1: 0.95 price; 6mo remaining;
            {
                "price": 0.95,
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                ),
                # APR = (1 - 0.95) / 0.95 / 0.5
                #     = 0.1052631579
                "expected_result": 0.1052631579,  # just over 10% APR
            },
            # test 2: 0.99 price; 6mo remaining;
            {
                "price": 0.99,
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                ),
                # APR = (1 - 0.99) / 0.99 / 0.5
                #     = 0.0202020202
                "expected_result": 0.0202020202,  # just over 2% APR
            },
            # test 3: 1.00 price; 6mo remaining;
            {
                "price": 1.00,  # 0% APR
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                ),
                # APR = (1 - 1) / 1 / 0.5
                #     = 0
                "expected_result": 0,  # 0% APR
            },
            # test 4: 0.95 price; 3mo remaining;
            {
                "price": 0.95,
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                ),
                # APR = (1 - 0.95) / 0.95 / 0.25
                #     = 0.2105263158
                "expected_result": 0.2105263158,  # just over 21% APR
            },
            # test 5: 0.95 price; 12mo remaining;
            {
                "price": 0.95,
                "time_remaining": StretchedTime(
                    days=365,  # 12 months = 1 years
                    time_stretch=1,
                ),
                # APR = (1 - 0.95) / 0.95 / 1
                #     = 0.05263157895
                "expected_result": 0.05263157895,  # just over 5% APR
            },
            # test 6: 0.10 price; 3mo remaining;
            {
                "price": 0.10,  # 0% APR
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                ),
                # APR = (1 - 0.10) / 0.10 / 0.25
                #     = 0
                "expected_result": 36,  # 3600% APR
            },
            # test 7: ERROR CASE
            #   -0.50 (negative) price; 3mo remaining;
            #   the function asserts that price > 0, so this case should raise an AssertionError
            {
                "price": -0.50,  # 0% APR
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                ),
                # APR = (1 - 0.10) / 0.10 / 0.25
                #     = 0
                "is_error_case": True,  # failure case
                "expected_result": AssertionError,
            },
            # test 8: ERROR CASE
            #   0.95 price; -3mo remaining (negative);
            #   the function asserts that normalized_time_remaining > 0, so this case \
            #   should raise an AssertionError
            {
                "price": 0.95,  # 0% APR
                "time_remaining": StretchedTime(
                    days=-91.25,  # -3 months = -0.25 years
                    time_stretch=1,
                ),
                # APR = (1 - 0.10) / 0.10 / 0.25
                #     = 0
                "is_error_case": True,  # failure case
                "expected_result": AssertionError,
            },
            # test 9: STRANGE RESULT CASE
            #   1.50 price (>1.00); 3mo remaining;
            #   the AMM math shouldn't let price be greater than 1
            {
                "price": 1.50,  # 0% APR
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                ),
                # APR = (1 - 1.50) / 1.50 / 0.25
                #     = -1.333333333
                "expected_result": -1.3333333333333333,  # strange result
            },
        ]

        for test_case in test_cases:

            # Check if this test case is supposed to fail
            if "is_error_case" in test_case and test_case["is_error_case"]:

                # Check that test case throws the expected error
                with self.assertRaises(test_case["expected_result"]):
                    apr = price_utils.calc_apr_from_spot_price(
                        price=test_case["price"], time_remaining=test_case["time_remaining"]
                    )

            # If test was not supposed to fail, continue normal execution
            else:
                apr = price_utils.calc_apr_from_spot_price(
                    price=test_case["price"], time_remaining=test_case["time_remaining"]
                )

                np.testing.assert_almost_equal(apr, test_case["expected_result"], err_msg="unexpected apr")

    def run_calc_spot_price_from_apr_test(self):
        """Unit tests for the calc_spot_price_from_apr function"""

        test_cases = [
            # test 1: 10% apr; 6mo remaining;
            {
                "apr": 0.10,  # 10% apr
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                ),
                # price = 1 / (1 + 0.10 * 0.5)
                #     = 0.1052631579
                "expected_result": 0.9523809524,  # just over 0.95
            },
            # test 2: 2% apr; 6mo remaining;
            {
                "apr": 0.02,  # 2% apr
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                ),
                # price = 1 / (1 + 0.02 * 0.5)
                #     = 0.9900990099
                "expected_result": 0.9900990099,  # just over 0.99
            },
            # test 3: 0% apr; 6mo remaining;
            {
                "apr": 0,  # 0% apr
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                ),
                # price = 1 / (1 + 0 * 0.5)
                #     = 1
                "expected_result": 1,
            },
            # test 4: 21% apr; 3mo remaining;
            {
                "apr": 0.21,  # 21% apr
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                ),
                # price = 1 / (1 + 0.21 * 0.25)
                #     = 0.2105263158
                "expected_result": 0.9501187648,  # just over 0.95
            },
            # test 5: 5% apr; 12mo remaining;
            {
                "apr": 0.05,  # 5% apr
                "time_remaining": StretchedTime(
                    days=365,  # 12 months = 1 years
                    time_stretch=1,
                ),
                # price = 1 / (1 + 0.05 * 1)
                #     = 0.05263157895
                "expected_result": 0.9523809524,  # just over 0.95
            },
            # test 6: 3600% apr; 3mo remaining;
            {
                "apr": 36,  # 3600% apr
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                ),
                # price = 1 / (1 + 36 * 0.25)
                #     = 0.1
                "expected_result": 0.10,
            },
            # test 7: 0% apr; 3mo remaining;
            {
                "apr": 0,  # 0% apr
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                ),
                # price = 1 / (1 + 0 * 0.25)
                #     = 0
                "expected_result": 1.00,
            },
            # test 8: 5% apr; no time remaining;
            {
                "apr": 5,  # 500% apr
                "time_remaining": StretchedTime(
                    days=0,  # 0 months = 0 years
                    time_stretch=1,
                ),
                # price = 1 / (1 + 5 * 0)
                #     = 0
                "expected_result": 1.00,
            },
        ]

        for test_case in test_cases:
            spot_price = price_utils.calc_spot_price_from_apr(
                apr=test_case["apr"], time_remaining=test_case["time_remaining"]
            )

            np.testing.assert_almost_equal(spot_price, test_case["expected_result"], err_msg="unexpected apr")

    # ### YieldSpace ###

    def run_calc_k_const_test(self):
        """Unit tests for calc_k_const function"""

        test_cases = [
            # test 1: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price; 3mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=500000,  # x = 500000
                    bond_reserves=500000,  # y = 500000
                    share_price=1,  # c = 1
                    init_share_price=1,  # u = 1
                ),
                "time_elapsed": 0.25,  # t = 0.25
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*500000)**0.25 + (2*500000+1*500000)**0.25
                #     = 61.587834600530776
                "expected_result": 61.587834600530776,
            },
            # test 2: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price; 12mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=500000,  # x = 500000
                    bond_reserves=500000,  # y = 500000
                    share_price=1,  # c = 1
                    init_share_price=1,  # u = 1
                ),
                "time_elapsed": 1,  # t = 1
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*500000)**1 + (2*500000+1*500000)**1
                #     = 2000000
                "expected_result": 2000000,
            },
            # test 3: 5M share_reserves; 5M bond_reserves
            #   2 share price; 1.5 init_share_price; 6mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=5000000,  # x = 5000000
                    bond_reserves=5000000,  # y = 5000000
                    share_price=2,  # c = 2
                    init_share_price=1.5,  # u = 1.5
                ),
                "time_elapsed": 0.50,  # t = 0.50
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*5000000)**0.50 + (2*5000000+1*5000000)**0.50
                #     = 61.587834600530776
                "expected_result": 8123.619671700687,
            },
            # test 4: 0M share_reserves; 5M bond_reserves
            #   2 share price; 1.5 init_share_price; 3mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=0,  # x = 0
                    bond_reserves=5000000,  # y = 5000000
                    share_price=2,  # c = 2
                    init_share_price=1.5,  # u = 1.5
                ),
                "time_elapsed": 0.25,  # t = 0.25
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 2/1.5 * (1*5000000)**0.25 + (2*5000000+1*5000000)**0.25
                #     = 61.587834600530776
                "expected_result": 56.23413251903491,
            },
            # test 5: 0 share_reserves; 0 bond_reserves
            #   2 share price; 1.5 init_share_price; 3mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=0,  # x = 0
                    bond_reserves=0,  # y = 0
                    share_price=2,  # c = 2
                    init_share_price=1.5,  # u = 1.5
                ),
                "time_elapsed": 0.25,  # t = 0.25
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 2/1.5 * (1*5000000)**0.25 + (2*5000000+1*5000000)**0.25
                #     = 61.587834600530776
                "expected_result": 0,
            },
            # test 6: ERROR CASE; 0 INIT SHARE PRICE
            #   5M share_reserves; 5M bond_reserves
            #   2 share price; 1.5 init_share_price; 6mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=5000000,  # x = 5000000
                    bond_reserves=5000000,  # y = 5000000
                    share_price=2,  # c = 2
                    init_share_price=0,  # ERROR CASE; u = 0
                ),
                "time_elapsed": 0.50,  # t = 0.50
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*5000000)**0.50 + (2*5000000+1*5000000)**0.50
                #     = 61.587834600530776
                "is_error_case": True,  # failure case
                "expected_result": ZeroDivisionError,
            },
        ]

        for test_case in test_cases:

            # Check if this test case is supposed to fail
            if "is_error_case" in test_case and test_case["is_error_case"]:

                # Check that test case throws the expected error
                with self.assertRaises(test_case["expected_result"]):
                    k = price_utils.calc_k_const(
                        market_state=test_case["market_state"],
                        time_elapsed=test_case["time_elapsed"],
                    )

            # If test was not supposed to fail, continue normal execution
            else:

                k = price_utils.calc_k_const(
                    market_state=test_case["market_state"],
                    time_elapsed=test_case["time_elapsed"],
                )

                np.testing.assert_almost_equal(k, test_case["expected_result"], err_msg="unexpected k")


class TestPriceUtils(BasePriceTest):
    """Test calculations for each of the price utility functions"""

    def test_calc_apr_from_spot_price(self):
        """Execute the test"""
        self.run_calc_apr_from_spot_price_test()

    def test_calc_k_const(self):
        """Execute the test"""
        self.run_calc_k_const_test()

    def test_calc_spot_price_from_apr(self):
        """Execute the test"""
        self.run_calc_spot_price_from_apr_test()

    def test_calc_liquidity(self):
        """Execute the test"""
        self.run_calc_liquidity_test(sim_utils.get_pricing_model("hyperdrive"))
        self.run_calc_liquidity_test(sim_utils.get_pricing_model("yieldspace"))