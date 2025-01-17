"""Dataclasses for all structs in the ERC4626HyperdriveDeployer contract."""
# super() call methods are generic, while our version adds values & types
# pylint: disable=arguments-differ
# contracts have PascalCase names
# pylint: disable=invalid-name
# contracts control how many attributes and arguments we have in generated code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# unable to determine which imports will be used in the generated code
# pylint: disable=unused-import
# we don't need else statement if the other conditionals all have return,
# but it's easier to generate
# pylint: disable=no-else-return
from __future__ import annotations


from dataclasses import dataclass


@dataclass
class Fees:
    """Fees struct."""

    curve: int
    flat: int
    governance: int


@dataclass
class PoolConfig:
    """PoolConfig struct."""

    baseToken: str
    initialSharePrice: int
    minimumShareReserves: int
    minimumTransactionAmount: int
    positionDuration: int
    checkpointDuration: int
    timeStretch: int
    governance: str
    feeCollector: str
    fees: Fees
    oracleSize: int
    updateGap: int
