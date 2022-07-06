from glQiwiApi import QiwiP2PClient
from config import QIWI_TOKEN


class QIWIManager:
    def __init__(self):
        self._p2p = QiwiP2PClient(secret_p2p=QIWI_TOKEN)
        self.paid = "PAID"

    async def create_payment(self, amount, comment):
        return await self._p2p.create_p2p_bill(amount=amount, comment=comment, bill_id=comment,
                                               pay_source_filter=["qw", "card"])

    async def check_payment(self, bill_id):
        return await self._p2p.get_bill_status(bill_id=bill_id)
