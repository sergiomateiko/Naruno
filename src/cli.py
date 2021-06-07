#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from wallet.wallet import Wallet_Create, Wallet_Import

from transactions.send_coin import send_coin
from node.node_connection import ndstart, ndstop, ndconnect, ndconnectmixdb, connect_to_main_network
from node.get_node_list import GetNodeList
from node.unl import save_new_unl_node

from lib.mixlib import banner_maker, menu_space, menu_maker, quit_menu_maker, question_maker

from blockchain.block.get_block import GetBlock, GetBlockFromOtherNode
from blockchain.block.create_block import CreateBlock

from lib.settings_system import the_settings, test_mode, debug_mode

from accounts.get_balance import GetBalance

def show_menu():
    """
    Prints some information and the menu.
    """

    print(banner_maker(sc_name="Decentra Network", description="This is an open source decentralized application network. In this network, you can develop and publish decentralized applications.", author="Decentra Network Developers"))


    print(menu_space() + \
	   menu_maker(menu_number="cw", menu_text="Create wallet")+ \
	   menu_space() + \
	   menu_maker(menu_number="sc", menu_text="Send Coin")+ \
       menu_space() + \
       menu_maker(menu_number="gb", menu_text="Get Balance")+ \
       menu_space() + \
       menu_maker(menu_number="ndstart", menu_text="Node Start")+ \
       menu_maker(menu_number="ndstop", menu_text="Node Stop")+ \
       menu_maker(menu_number="ndconnect", menu_text="Node Connect")+ \
       menu_maker(menu_number="connectmainnetwork", menu_text="Connect to Main Network")+ \
       menu_maker(menu_number="ndconnectmixdb", menu_text="Node Connect from mixdb")+ \
       menu_maker(menu_number="ndnewunl", menu_text="Add new UNL node")+ \
       menu_space() + \
       menu_maker(menu_number="testmodeon", menu_text="Test mode ON")+ \
       menu_maker(menu_number="testmodeoff", menu_text="Test mode OF")+ \
       menu_maker(menu_number="debugmodeon", menu_text="Debug mode ON")+ \
       menu_maker(menu_number="debugmodeoff", menu_text="Debug mode OF")+ \
       menu_space() + \
       menu_maker(menu_number="getfullnodelist", menu_text="Get Full Node List")+ \
       menu_maker(menu_number="getblock", menu_text="Get block From Other Nodes")+ \
       menu_space())


    print(quit_menu_maker(mode="main"))


def menu():
    """
    The main structure of the cli mode, this function prints the menu, 
    listens to the entries, makes the directions.
    """

    while True:
        show_menu()
        choices_input = question_maker(mode="main")

        if choices_input == "connectmainnetwork":
            connect_to_main_network()
        if choices_input == "cw":
            Wallet_Create()
        if choices_input == "sc":
            temp_coin_amount = input("Coin Amount (ex. 1.0): ")
            type_control = False
            try:
                float(temp_coin_amount)
                type_control = True
            except:
                print("This is not float coin amount.")

            if type_control and not float(temp_coin_amount) < GetBlock().minumum_transfer_amount:
                send_coin(float(temp_coin_amount), input("Please write receiver adress: "))

        if choices_input == "gb":
            print(GetBalance(Wallet_Import(0,0), GetBlock()))
            print(Wallet_Import(0,3))
        if choices_input == "help":
            show_menu()
        if choices_input == "ndstart":
            ndstart(str(input("ip: ")), int(input("port: ")))
        if choices_input == "ndstop":
            ndstop()
        if choices_input == "ndconnect":
            ndconnect(str(input("node ip: ")), int(input("node port: ")))

        if choices_input == "ndconnectmixdb":
            ndconnectmixdb()
        if choices_input == "ndnewunl":
            save_new_unl_node(input("Please write ID of the node: "))
        if choices_input == "testmodeon":
            test_mode(True)
        if choices_input == "testmodeoff":
            test_mode(False)
        if choices_input == "debugmodeon":
            debug_mode(True)
            # from node.myownp2pn import mynode
            # mynode.main_node.debug = True
        if choices_input == "debugmodeoff":
            debug_mode(False)
            # from node.myownp2pn import mynode
            # mynode.main_node.debug = False

        if choices_input == "getfullnodelist":
            GetNodeList()
        if choices_input == "getblock":
            if the_settings()["test_mode"]:
                CreateBlock()
            else:
                GetBlockFromOtherNode()



        if choices_input == "0":
            exit()


if __name__ == '__main__':
    menu()