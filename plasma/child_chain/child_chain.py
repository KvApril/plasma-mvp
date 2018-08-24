from plasma_core.block import Block
from plasma_core.chain import Chain
from plasma_core.utils.transactions import get_deposit_tx, encode_utxo_id
from .root_event_listener import RootEventListener


import rlp
from ethereum import utils
from plasma_core.utils.address import address_to_hex

class ChildChain(object):

    def __init__(self, operator, root_chain):
        self.operator = operator
        self.root_chain = root_chain
        self.chain = Chain(self.operator)
        self.current_block = Block(number=self.chain.next_child_block)

        # Listen for events
        self.event_listener = RootEventListener(root_chain, confirmations=0)
        self.event_listener.on('Deposit', self.apply_deposit)
        self.event_listener.on('ExitStarted', self.apply_exit)

    def apply_exit(self, event):
        event_args = event['args']
        utxo_id = event_args['utxoPos']
        self.chain.mark_utxo_spent(utxo_id)

    def apply_deposit(self, event):
        event_args = event['args']
        owner = event_args['depositor']
        amount = event_args['amount']
        blknum = event_args['depositBlock']

        deposit_tx = get_deposit_tx(owner, amount)
        deposit_block = Block([deposit_tx], number=blknum)
        self.chain.add_block(deposit_block)

    def apply_transaction(self, tx):
        self.chain.validate_transaction(tx, self.current_block.spent_utxos)
        self.current_block.add_transaction(tx)
        return encode_utxo_id(self.current_block.number, len(self.current_block.transaction_set) - 1, 0)

    def submit_block(self, block):
        if isinstance(block, str):
            block = rlp.decode(utils.decode_hex(block), Block)

        self.chain.add_block(block)
        self.root_chain.transact({
            'from': utils.checksum_encode(address_to_hex(self.operator))
        }).submitBlock(block.merkle.root)
        self.current_block = Block(number=self.chain.next_child_block)

    def get_transaction(self, tx_id):
        return self.chain.get_transaction(tx_id)

    def get_block(self, blknum):
        return rlp.encode(self.chain.get_block(blknum), Block).hex()

    def get_current_block(self):
        return rlp.encode(self.current_block, Block).hex()
