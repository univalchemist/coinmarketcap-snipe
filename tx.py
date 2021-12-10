from web3 import Web3
import json, requests
import settingparser as sp
from log import logbook
from web3.gas_strategies.time_based import medium_gas_price_strategy

INFO = logbook().createINFOLogger()
ERROR = logbook().createERRORLogger()
logger = logbook()

class Txn_bot():
    def __init__(self, token_address):
        self.w3 = self.connect()
        self.WBNB = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
        self.BUSD = Web3.toChecksumAddress("0xe9e7cea3dedca5984780bafc599bd69add087d56")
        self.address = Web3.toChecksumAddress(sp.GetAddress())
        self.private_key = sp.GetSecretKey()
        self.token_address = Web3.toChecksumAddress(token_address)
        self.token_contract = self.set_token_contract()
        self.router_address, self.router = self.set_router()
        self.BUSD_contract = self.set_BUSD_contract()
        self.gas_price = sp.GetGasPrice() * (10**9)
        self.max_fee_per_gas = sp.GetMaxFeePerGas()
        self.max_priority_fee_per_gass = sp.GetMaxPriorityFeePerGas()
        self.loadTradeList()

    def connect(self):
        # rpc = "https://eth-mainnet.alchemyapi.io/v2/YVWTxFc3_rjUyNOPuuapSak5BAk1iUSZ"
        # w3 = Web3(Web3.HTTPProvider(rpc))
        w3 = Web3(Web3.HTTPProvider(sp.GetRPC()))
        return w3

    def get_token_decimals(self):
        return self.token_contract.functions.decimals().call()

    def get_token_symbol(self):
        return self.token_contract.functions.symbol().call()

    def get_token_name(self):
        return self.token_contract.functions.name().call()

    def set_router(self):
        router_address = Web3.toChecksumAddress("0xde937d83e62764c1f4809b87d4c8c5779c351fbf") 
        with open("./ABIS/BSC_Swapper.json") as f:
            contract_abi = json.load(f)
        router = self.w3.eth.contract(address=router_address, abi=contract_abi)
        return router_address, router

    def set_token_contract(self):
        with open("./ABIS/bep20_abi_token.json") as f:
            contract_abi = json.load(f)
        token_contract = self.w3.eth.contract(address=self.token_address, abi=contract_abi)
        return token_contract

    def set_BUSD_contract(self):
        with open("./ABIS/bep20_abi_token.json") as f:
            contract_abi = json.load(f)
        token_contract = self.w3.eth.contract(address=self.BUSD, abi=contract_abi)
        return token_contract

    def get_token_balance(self): 
        return self.token_contract.functions.balanceOf(self.address).call() / (10 ** self.token_contract.functions.decimals().call())

    def get_balance_of_account(self):
        return self.w3.fromWei(self.w3.eth.get_balance(self.address), "ether")

    def get_gas_price(self):
        return self.w3.eth.gas_price / 10**9
        # return self.w3.fromWei(self.w3.eth.gas_price, "ether")

    def getOutputfromTokentoBUSD(self):
        AmountBUSD = self.router.functions.getOutputfromTokentoBUSD(
            self.token_contract.functions.balanceOf(self.address).call(),
            self.token_address
            ).call()
        return float(Web3.fromWei(AmountBUSD,"ether"))

    def fromBNBtoToken(self):
        try:
            Amount = int(sp.GetAmountPerBuy() * (10**18))
            txn = self.router.functions.fromBNBtoToken(
                self.token_address
            ).buildTransaction(
                {"from": self.address,
                "gas": 500000,
                "gasPrice": self.gas_price,
                # "maxPriorityFeePerGas": self.w3.toWei(self.max_priority_fee_per_gass, "gwei"),
                "nonce": self.w3.eth.getTransactionCount(self.address), # nonce - a counter that indicates the number of transactions sent from the account.
                "value": int(Amount)}
                )
            txn.update({ "gas" : int(self.estimateGas(txn))})
            signed_txn = self.w3.eth.account.sign_transaction(
                txn,
                self.private_key
            )
            txn = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            logger.success("TX Hash: " + str(txn.hex()))
            txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn)
            if txn_receipt["status"] == 1:
                self.TradeList.append(self.token_address), self.saveTradeList()
                return True,"BUY TX Successfull!"
            else: return False, "BUY TX Faild!"
        except Exception as e:
            print(e)
            return False, "BUY TX Failed!"
    
    def fromTokentoBNB(self):
        try:
            self.approve()
            txn = self.router.functions.fromTokentoBNB(
                int(self.token_contract.functions.balanceOf(self.address).call()),
                self.token_address
            ).buildTransaction(
                {"from": self.address, 
                "gas": 550000,
                "gasPrice": self.gas_price,
                # "maxPriorityFeePerGas": self.w3.toWei(self.max_priority_fee_per_gass, "gwei"),
                "nonce": self.w3.eth.getTransactionCount(self.address), 
                "value": 0}
                )
            txn.update({ "gas" : int(self.estimateGas(txn))})
            signed_txn = self.w3.eth.account.sign_transaction(
                txn,
                self.private_key
            )
            txn = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            logger.info("SELL Hash: " + str(txn.hex()))
            txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn)
            if txn_receipt["status"] == 1:
                self.TradeList.remove(self.token_address), self.saveTradeList()
                return True,"SELL Transaction Successfull!" 
            else: return False, "SELL Transaction Faild!"
        except Exception as e:
            print(e)
            return False,  "SELL Transaction Faild!"


    def estimateGas(self, txn):
        gas = self.w3.eth.estimateGas({
                    "from": txn["from"],
                    "to": txn["to"],
                    "value": txn["value"],
                    "data": txn["data"]})
        gas = gas + (gas / 10) # Adding 1/10 from gas to gas!
        return gas

    def getMaxPriorityFeePerGas(self):
        tip = self.w3.eth.max_priority_fee
        tip = tip + 1
        return tip

    def generateGasPrice(self):
        self.w3.eth.set_gas_price_strategy(medium_gas_price_strategy)
        tip = self.w3.eth.generate_gas_price()
        tip = tip + 1
        return tip

    def fromBUSDtoToken(self):
        self.approveBUSD()
        try:
            Amount = int(sp.GetAmountPerBuy() * (10**18))
            txn = self.router.functions.fromBUSDtoToken(
                Amount,
                self.token_address
            ).buildTransaction(
                {"from": self.address, 
                "gas": 600000,
                "gasPrice": self.gas_price,
                # "maxPriorityFeePerGas": self.w3.toWei(self.max_priority_fee_per_gass, "gwei"),
                "nonce": self.w3.eth.getTransactionCount(self.address), 
                "value": 0}
                )
            txn.update({ "gas" : int(self.estimateGas(txn))})
            signed_txn = self.w3.eth.account.sign_transaction(
                txn,
                self.private_key
            )
            txn = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            print("BUY Hash:", txn.hex()  )
            txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn)
            if txn_receipt["status"] == 1:
                self.TradeList.append(self.token_address), self.saveTradeList()
                return True, "BUY Transaction Successfull!"
            else: return False,  "BUY Transaction Faild!"
        except Exception as e:
            ERROR.error(e)
            print(e)
            return False,  "BUY Transaction Faild!"


    def fromTokentoBUSD(self):
        self.approve()
        try:
            Token_Amount = self.token_contract.functions.balanceOf(self.address).call()
            txn = self.router.functions.fromTokentoBUSD(
                Token_Amount,
                self.token_address
            ).buildTransaction(
                {"from": self.address, 
                "gas": 850000,
                "gasPrice": self.gas_price,
                # "maxPriorityFeePerGas": self.w3.toWei(self.max_priority_fee_per_gass, "gwei"),
                "nonce": self.w3.eth.getTransactionCount(self.address), 
                "value": 0}
                )
            txn.update({ "gas" : int(self.estimateGas(txn))})
            signed_txn = self.w3.eth.account.sign_transaction(
                txn,
                self.private_key
            )
            txn = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            print("SELL TOKENS :",txn.hex()  )
            txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn)
            if txn_receipt["status"] == 1:
                self.TradeList.remove(self.token_address), self.saveTradeList()
                return True, "SELL Transaction Successfull!"  
            else: return False,  "SELL Transaction Faild!"  
        except Exception as e:
            print(e)

    def is_approve(self):
        Approve = self.token_contract.functions.allowance(self.address ,self.router_address).call()
        Aproved_quantity = self.token_contract.functions.balanceOf(self.address).call()
        if int(Approve) <= int(Aproved_quantity):
            return False
        else:
            return True

    def approve(self):
        if self.is_approve() == False:
            try:
                txn = self.token_contract.functions.approve(
                    self.router_address,
                    115792089237316195423570985008687907853269984665640564039457584007913129639935 # Max Approve
                ).buildTransaction(
                    {"from": self.address, 
                    "gas": 100000,
                    "gasPrice": self.gas_price,
                    # "maxPriorityFeePerGas": self.w3.toWei(self.max_priority_fee_per_gass, "gwei"),
                    "nonce": self.w3.eth.getTransactionCount(self.address), 
                    "value": 0}
                    )
                txn.update({ "gas" : int(self.estimateGas(txn))})
                signed_txn = self.w3.eth.account.sign_transaction(
                    txn,
                    self.private_key
                )
                
                txn = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn)   
                if txn_receipt["status"] == 1:
                    logger.success("Approve Successful!")
                    return True
                else:
                    logger.error("Approve Transaction Failed!" )
                    return False
            except Exception as e:
                logger.error("Approve Transaction Failed!")
                print(e)
                return False
        else:
            logger.success("Already approved!")
            return True


    def is_approveBUSD(self):
        Approve = self.BUSD_contract.functions.allowance(self.address ,self.router_address).call()
        Aproved_quantity = self.BUSD_contract.functions.balanceOf(self.address).call()
        if int(Approve) <= int(Aproved_quantity):
            return False
        else:
            return True

    def approveBUSD(self):
        if self.is_approveBUSD() == False:
            try:
                txn = self.BUSD_contract.functions.approve(
                    self.router_address,
                    115792089237316195423570985008687907853269984665640564039457584007913129639935 # Max Approve
                ).buildTransaction(
                    {"from": self.address, 
                    "gas": 100000,
                    "gasPrice": self.gas_price,
                    # "maxPriorityFeePerGas": self.w3.toWei(self.max_priority_fee_per_gass, "gwei"),
                    "nonce": self.w3.eth.getTransactionCount(self.address), 
                    "value": 0}
                    )
                txn.update({ "gas" : int(self.estimateGas(txn))})
                signed_txn = self.w3.eth.account.sign_transaction(
                    txn,
                    self.private_key
                )
                txn = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn)   
                if txn_receipt["status"] == 1:
                    logger.success("Approve Successfull!")
                    return True 
                else:
                    logger.error("Approve Transaction Faild!")
                    return False
            except Exception as e:
                logger.error("Approve Transaction Faild!")
                print(e)
                return False
        else:
            logger.success("Allready approved!")
            return True

    def loadTradeList(self):
        with open("tradelist.json","r") as e:
            self.TradeList = json.load(e)

    def saveTradeList(self):
        with open("tradelist.json","w") as e:
            json.dump(self.TradeList, e)