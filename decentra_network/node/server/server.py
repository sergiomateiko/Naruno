#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from threading import Thread
import socket
import json
from hashlib import sha256
import os

from decentra_network.blockchain.block.change_transaction_fee import \
    ChangeTransactionFee
from decentra_network.blockchain.block.get_block import GetBlock
from decentra_network.blockchain.block.save_block import SaveBlock
from decentra_network.config import CONNECTED_NODES_PATH
from decentra_network.config import LOADING_BLOCK_PATH
from decentra_network.config import LOADING_ACCOUNTS_PATH
from decentra_network.config import LOADING_BLOCKSHASH_PATH
from decentra_network.config import LOADING_BLOCKSHASH_PART_PATH
from decentra_network.config import TEMP_ACCOUNTS_PATH
from decentra_network.config import TEMP_BLOCK_PATH
from decentra_network.config import TEMP_BLOCKSHASH_PATH
from decentra_network.config import TEMP_BLOCKSHASH_PART_PATH
from decentra_network.lib.config_system import get_config
from decentra_network.lib.log import get_logger
from decentra_network.lib.merkle_root import MerkleTree
from decentra_network.node.unl import Unl
from decentra_network.transactions.check.check_transaction import \
    CheckTransaction
from decentra_network.transactions.get_transaction import GetTransaction
from decentra_network.transactions.transaction import Transaction
from decentra_network.wallet.ellipticcurve.ecdsa import Ecdsa
from decentra_network.wallet.ellipticcurve.privateKey import PrivateKey
from decentra_network.wallet.ellipticcurve.publicKey import PublicKey
from decentra_network.wallet.ellipticcurve.signature import Signature
from decentra_network.wallet.wallet_import import wallet_import
from decentra_network.node.client.client import client
import time
import contextlib

logger = get_logger("NODE")




class server(Thread):
    Server = None
    id = wallet_import(0, 0)
    def __init__(self, host, port, save_messages=False, test=False):
        self.__class__.Server = self      
        Thread.__init__(self)
        self.running = True
        
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)

        self.clients = []

        self.candidate_block = None
        self.candidate_block_hash = None
        self.messages = []
        self.save_messages = False

        self.start()

    def run(self):
        self.sock.settimeout(10.0)
        while self.running:
            with contextlib.suppress(socket.timeout):
                conn, addr = self.sock.accept()
                connected = any(a_client.socket == conn for a_client in self.clients)
                data = conn.recv(4096)
                conn.send(server.id.encode("utf-8"))
                client_id = data.decode("utf-8")
                if Unl.node_is_unl(client_id):
                    self.clients.append(client(conn, addr, client_id, self))
                    server.save_connected_node(addr[0], addr[1], client_id)
            time.sleep(0.01)
        for c in self.clients:
            c.stop()
        time.sleep(1)
        for c in self.clients:
            c.join()
        self.sock.settimeout(None)
        self.sock.close()

    def stop(self):
        self.running = False
    
    def send(self, data):
        data["id"] = server.id
        sign = Ecdsa.sign(
                        str(data["action"]),
                        PrivateKey.fromPem(wallet_import(0, 1)),
                    ).toBase64()

        data["sign"] = sign
        for a_client in self.clients:
            a_client.socket.sendall(json.dumps(data).encode("utf-8"))
        return data
    
    def check_message(self, data):
        message = str(data["action"])
        return Ecdsa.verify(
                        message,
                        Signature.fromBase64(data["sign"]),
                        PublicKey.fromPem(data["id"]),
                    )
    
    def connect(self, host, port):
        connected = any(a_client.host == host and a_client.port == port for a_client in self.clients)
        if not connected:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            addr = (host, port)
            conn.connect(addr)
            conn.send(server.id.encode("utf-8"))
            client_id = conn.recv(4096).decode("utf-8")                
            if Unl.node_is_unl(client_id):
                    self.clients.append(client(conn, addr, client_id, self))


    @staticmethod
    def get_connected_nodes():
        """
        Returns the connected nodes.
        """

        if not os.path.exists(CONNECTED_NODES_PATH):
            return {}

        the_pending_list = {}
        os.chdir(get_config()["main_folder"])
        for entry in os.scandir(CONNECTED_NODES_PATH):
            if entry.name != "README.md":
                with open(entry.path, "r") as my_transaction_file:
                    loaded_json = json.load(my_transaction_file)
                    the_pending_list[loaded_json["id"]] = loaded_json

        return the_pending_list



    @staticmethod
    def save_connected_node(host, port, node_id):
        """
        Saves the connected nodes.
        """

        node_list = {}
        node_list["id"] = node_id
        node_list["host"] = host
        node_list["port"] = port

        node_id = sha256((node_id).encode("utf-8")).hexdigest()
        file_name = CONNECTED_NODES_PATH + f"{node_id}.json"
        os.chdir(get_config()["main_folder"])
        with open(file_name, "w") as connected_node_file:
            json.dump(node_list, connected_node_file, indent=4)

    @staticmethod
    def connectionfrommixdb():
        """
        Connects to the mixdb.
        """

        node_list = server.Server.get_connected_nodes()

        for element in node_list:
            server.Server.connect(node_list[element]["host"],
                                           node_list[element]["port"])

    @staticmethod
    def connected_node_delete(node_id):
        """
        Deletes a connected node.
        """
        os.chdir(get_config()["main_folder"])
        node_id = sha256((node_id).encode("utf-8")).hexdigest()
        for entry in os.scandir(CONNECTED_NODES_PATH):
            if entry.name == f"{node_id}.json":
                os.remove(entry.path)


    def get_message(self, node, data):
        is_unl = Unl.node_is_unl(node.id)
        if "sendmefullblock" in data:
            self.send_full_chain(node)

        if ("fullblock" in data and is_unl
                    and Ecdsa.verify(
                        "fullblock" + data["byte"],
                        Signature.fromBase64(data["signature"]),
                        PublicKey.fromPem(node.id),
                    )):
                logger.info("getting chain")
                self.get_full_chain(data, node)

        if ("fullaccounts" in data and is_unl
                    and Ecdsa.verify(
                        "fullaccounts" + data["byte"],
                        Signature.fromBase64(data["signature"]),
                        PublicKey.fromPem(node.id),
                    )):
                logger.info("get_full_accounts")
                self.get_full_accounts(data, node)


        if ("fullblockshash" in data and is_unl
                    and Ecdsa.verify(
                        "fullblockshash" + data["byte"],
                        Signature.fromBase64(data["signature"]),
                        PublicKey.fromPem(node.id),
                    )):
                self.get_full_blockshash(data, node)


        if ("fullblockshash_part" in data and is_unl
                    and Ecdsa.verify(
                        "fullblockshash_part" + data["byte"],
                        Signature.fromBase64(data["signature"]),
                        PublicKey.fromPem(node.id),
                    )):
                self.get_full_blockshash_part(data, node)

        if "transactionrequest" in data:
                self.get_transaction(data, node)

        if "action" in data:
            if data["action"] == "myblock":
                    self.get_candidate_block(data, node)


            if data["action"] == "myblockhash":
                    self.get_candidate_block_hash(data, node)


    def send_my_block(self, block, nodes):
        system = block

        new_list = []

        signature_list = []

        for element in system.validating_list:
            new_list.append(element.dump_json())
            signature_list.append(element.signature)

        Merkle_signature_list = (MerkleTree(signature_list).getRootHash()
                                 if len(signature_list) != 0 else "0")

        data = {
            "action":
            "myblock",
            "transaction":
            new_list,
            "sequance_number":
            system.sequance_number,
            "signature":
            Ecdsa.sign(
                f"myblock{Merkle_signature_list}{str(system.sequance_number)}",
                PrivateKey.fromPem(wallet_import(0, 1)),
            ).toBase64(),
        }

        for each_node in nodes:
            self.send_data(each_node, data)

    def send_my_block_hash(self, block, nodes):
        system = block

        if system.raund_1 and not system.raund_2:

            data = {
                "action":
                "myblockhash",
                "hash":
                system.hash,
                "sequance_number":
                system.sequance_number,
                "signature":
                Ecdsa.sign(
                    f"myblockhash{system.hash}{str(system.sequance_number)}",
                    PrivateKey.fromPem(wallet_import(0, 1)),
                ).toBase64(),
            }

            for each_node in nodes:
                self.send_data(each_node, data)

    def get_candidate_block(self, data, node):

        if (not Unl.node_is_unl(node.id)
                or GetBlock().sequance_number != data["sequance_number"]):
            return
        signature_list = [
            element["signature"] for element in data["transaction"]
        ]
        merkle_root_of_signature_list = (
            MerkleTree(signature_list).getRootHash()
            if signature_list else "0")

        if Ecdsa.verify(
            (f"myblock{merkle_root_of_signature_list}" +
             str(data["sequance_number"])),
                Signature.fromBase64(data["signature"]),
                PublicKey.fromPem(node.id),
        ):

            temp_tx = [
                Transaction.load_json(element)
                for element in data["transaction"]
            ]

            data["transaction"] = temp_tx

            node.candidate_block = data

    def get_candidate_block_hash(self, data, node):

        if (Unl.node_is_unl(node.id) and GetBlock().sequance_number
                == data["sequance_number"]) and Ecdsa.verify(
                    "myblockhash" + data["hash"] +
                    str(data["sequance_number"]),
                    Signature.fromBase64(data["signature"]),
                    PublicKey.fromPem(node.id),
                ):
            data["sender"] = node.id

            node.candidate_block_hash = data

    def send_full_chain(self, node=None):
        self.send_full_accounts(node)
        self.send_full_blockshash(node)
        file = open(TEMP_BLOCK_PATH, "rb")
        SendData = file.read(1024)
        while SendData:

            data = {
                "fullblock":
                1,
                "byte": (SendData.decode(encoding="iso-8859-1")),
                "signature":
                Ecdsa.sign(
                    "fullblock" + str(
                        (SendData.decode(encoding="iso-8859-1"))),
                    PrivateKey.fromPem(wallet_import(0, 1)),
                ).toBase64(),
            }
            if node is not None:
                self.send_data(node, data)
            else:
                self.send_data_all(data)

            SendData = file.read(1024)

            if not SendData:
                data = {
                    "fullblock":
                    1,
                    "byte":
                    "end",
                    "signature":
                    Ecdsa.sign("fullblock" + "end",
                               PrivateKey.fromPem(wallet_import(
                                   0, 1))).toBase64(),
                }
                if node is not None:
                    self.send_data(node, data)
                else:
                    self.send_data_all(data)

    def send_full_accounts(self, node=None):
        file = open(TEMP_ACCOUNTS_PATH, "rb")
        SendData = file.read(1024)
        while SendData:

            data = {
                "fullaccounts":
                1,
                "byte": (SendData.decode(encoding="iso-8859-1")),
                "signature":
                Ecdsa.sign(
                    "fullaccounts" + str(
                        (SendData.decode(encoding="iso-8859-1"))),
                    PrivateKey.fromPem(wallet_import(0, 1)),
                ).toBase64(),
            }
            if node is not None:
                self.send_data(node, data)
            else:
                self.send_data_all(data)

            SendData = file.read(1024)

            if not SendData:
                data = {
                    "fullaccounts":
                    1,
                    "byte":
                    "end",
                    "signature":
                    Ecdsa.sign("fullaccounts" + "end",
                               PrivateKey.fromPem(wallet_import(
                                   0, 1))).toBase64(),
                }
                if node is not None:
                    self.send_data(node, data)
                else:
                    self.send_data_all(data)

    def send_full_blockshash(self, node=None):
        file = open(TEMP_BLOCKSHASH_PATH, "rb")
        SendData = file.read(1024)
        while SendData:

            data = {
                "fullblockshash":
                1,
                "byte": (SendData.decode(encoding="iso-8859-1")),
                "signature":
                Ecdsa.sign(
                    "fullblockshash" + str(
                        (SendData.decode(encoding="iso-8859-1"))),
                    PrivateKey.fromPem(wallet_import(0, 1)),
                ).toBase64(),
            }
            if node is not None:
                self.send_data(node, data)
            else:
                self.send_data_all(data)

            SendData = file.read(1024)

            if not SendData:
                data = {
                    "fullblockshash":
                    1,
                    "byte":
                    "end",
                    "signature":
                    Ecdsa.sign(
                        "fullblockshash" + "end",
                        PrivateKey.fromPem(wallet_import(0, 1)),
                    ).toBase64(),
                }
                if node is not None:
                    self.send_data(node, data)
                else:
                    self.send_data_all(data)

    def send_full_blockshash_part(self, node=None):
        file = open(TEMP_BLOCKSHASH_PART_PATH, "rb")
        SendData = file.read(1024)
        while SendData:

            data = {
                "fullblockshash_part":
                1,
                "byte": (SendData.decode(encoding="iso-8859-1")),
                "signature":
                Ecdsa.sign(
                    "fullblockshash_part" + str(
                        (SendData.decode(encoding="iso-8859-1"))),
                    PrivateKey.fromPem(wallet_import(0, 1)),
                ).toBase64(),
            }
            if node is not None:
                self.send_data(node, data)
            else:
                self.send_data_all(data)

            SendData = file.read(1024)

            if not SendData:
                data = {
                    "fullblockshash_part":
                    1,
                    "byte":
                    "end",
                    "signature":
                    Ecdsa.sign(
                        "fullblockshash_part" + "end",
                        PrivateKey.fromPem(wallet_import(0, 1)),
                    ).toBase64(),
                }
                if node is not None:
                    self.send_data(node, data)
                else:
                    self.send_data_all(data)

    def get_full_chain(self, data, node):

        get_ok = False

        if not os.path.exists(TEMP_BLOCK_PATH):
            get_ok = True
        else:
            system = GetBlock()
            if node.id == system.dowload_true_block:
                get_ok = True

        if get_ok:

            if str(data["byte"]) == "end":

                os.rename(LOADING_BLOCK_PATH, TEMP_BLOCK_PATH)

                from consensus.consensus_main import consensus_trigger

                from decentra_network.lib.perpetualtimer import perpetualTimer

                system = GetBlock()
                system.newly = True

                ChangeTransactionFee(system)

                system.exclude_validators = []
                perpetualTimer(system.consensus_timer,
                               consensus_trigger).start()
                SaveBlock(system)

            else:
                file = open(LOADING_BLOCK_PATH, "ab")

                file.write((data["byte"].encode(encoding="iso-8859-1")))
                file.close()

    def get_full_blockshash(self, data, node):

        get_ok = False

        if not os.path.exists(TEMP_BLOCKSHASH_PATH):
            get_ok = True
        else:
            system = GetBlock()
            if node.id == system.dowload_true_block:
                get_ok = True

        if get_ok:
            if str(data["byte"]) == "end":
                os.rename(LOADING_BLOCKSHASH_PATH, TEMP_BLOCKSHASH_PATH)
            else:
                file = open(LOADING_BLOCKSHASH_PATH, "ab")
                file.write((data["byte"].encode(encoding="iso-8859-1")))
                file.close()
                            

    def get_full_blockshash_part(self, data, node):

        get_ok = False

        if not os.path.exists(TEMP_BLOCKSHASH_PART_PATH):
            get_ok = True
        else:
            system = GetBlock()
            if node.id == system.dowload_true_block:
                get_ok = True

        if get_ok:
            if str(data["byte"]) == "end":
                os.rename(LOADING_BLOCKSHASH_PART_PATH, TEMP_BLOCKSHASH_PART_PATH)
            else:
                file = open(LOADING_BLOCKSHASH_PART_PATH, "ab")
                file.write((data["byte"].encode(encoding="iso-8859-1")))
                file.close()

    def get_full_accounts(self, data, node):

        get_ok = False

        if not os.path.exists(TEMP_ACCOUNTS_PATH):
            get_ok = True
        else:
            system = GetBlock()
            if node.id == system.dowload_true_block:
                get_ok = True

        if get_ok:
            if str(data["byte"]) == "end":
                os.rename(LOADING_ACCOUNTS_PATH, TEMP_ACCOUNTS_PATH)
            else:
                file = open(LOADING_ACCOUNTS_PATH, "ab")
                file.write((data["byte"].encode(encoding="iso-8859-1")))
                file.close()

    @staticmethod
    def send_transaction(tx):
        """
        Sends the given transaction to UNL nodes.
        """

        items = {
            "transactionrequest": 1,
            "sequance_number": tx.sequance_number,
            "signature": tx.signature,
            "fromUser": tx.fromUser,
            "to_user": tx.toUser,
            "data": tx.data,
            "amount": tx.amount,
            "transaction_fee": tx.transaction_fee,
            "transaction_time": tx.transaction_time,
        }
        for each_node in Unl.get_as_node_type(Unl.get_unl_nodes()):
            server.Server.send_data(each_node, items)

    def get_transaction(self, data, node):
        block = GetBlock()
        the_transaction = Transaction(
            data["sequance_number"],
            data["signature"],
            data["fromUser"],
            data["to_user"],
            data["data"],
            data["amount"],
            data["transaction_fee"],
            data["transaction_time"],
        )
        if GetTransaction(block, the_transaction):
            server.send_transaction(the_transaction)
            SaveBlock(block)

    def send_block_to_other_nodes(self):
        """
        Sends the block to the other nodes.
        """
        self.send_full_chain()
        self.send_full_accounts()
        self.send_full_blockshash()
        self.send_full_blockshash_part()
