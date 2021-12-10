import json

def openSettings():
    with open("settings.json", "r") as s:
        return json.load(s)

def GetSecretKey():
    return openSettings()["SecretKey"]

def GetAddress():
    return openSettings()["Address"]

def GetGasPrice():
    return openSettings()["GasPrice"]

def GetMaxFeePerGas():
    return openSettings()["maxFeePerGas"]

def GetMaxPriorityFeePerGas():
    return openSettings()["maxPriorityFeePerGas"]

def GetRPC():
    return openSettings()["RPC"]

def GetSwapContract():
    return openSettings()["Swap_Contract"]

def GetChainName():
    return openSettings()["ChainName"]

def GetMaxTokenTax():
    return openSettings()["MaximumTokenTAX"]

def GetCurrency():
    return openSettings()["Currency"]

def GetAmountPerBuy():
    return openSettings()["AmountPerBuy"]

def GetTakeProfit():
    return openSettings()["TakeProfit"]

def GetStopLost():
    return openSettings()["StopLost"]

def GetTrailingStopLoss():
    return openSettings()["TrailingStopLoss"]
    
