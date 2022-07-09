#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import pickle

from config import BLOCKS_PATH


def GetBlockstoBlockchainDB(
    sequance_number,
    custom_BLOCKS_PATH=None,
    custom_TEMP_ACCOUNTS_PATH=None,
    custom_TEMP_BLOCKSHASH_PATH=None,
    custom_TEMP_BLOCKSHASH_PART_PATH=None,
):
    """
    Gets the block from the blockchain database
    """
    try:
        the_BLOCKS_PATH = (BLOCKS_PATH if custom_BLOCKS_PATH is None else
                           custom_BLOCKS_PATH)
        with open(the_BLOCKS_PATH + str(sequance_number) + ".block",
                  "rb") as block_file:
            the_block = pickle.load(block_file)

        with open(the_BLOCKS_PATH + str(sequance_number) + ".accounts",
                  "rb") as block_file:
            the_accounts = pickle.load(block_file)

        with open(the_BLOCKS_PATH + str(sequance_number) + ".blockshash",
                  "rb") as block_file:
            the_blockshash = pickle.load(block_file)

        with open(the_BLOCKS_PATH + str(sequance_number) + ".blockshashpart",
                  "rb") as block_file:
            the_blockshashpart = pickle.load(block_file)

        return [the_block, the_accounts, the_blockshash, the_blockshashpart]
    except FileNotFoundError:
        return False