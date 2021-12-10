import json
from logging import error
import time
from requests_html import HTMLSession
from hpcheck import HoneyPotChecker
import settingparser as sp
from log import logbook
from tx import Txn_bot
from threading import Thread as T
from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urljoin
import datetime as dt

session = HTMLSession()

# Logger
logger = logbook()

class TakeProfitStopLoss():

    def __init__(self, Taddress):
        self.TokenAddress = Taddress
        self.TX = Txn_bot(Taddress)
        self.TokenName = self.TX.get_token_name()
        self.TakeProfitPrice = sp.GetAmountPerBuy() + ((sp.GetAmountPerBuy()/100)*sp.GetTakeProfit())
        self.StopLostPrice = sp.GetAmountPerBuy() - ((sp.GetAmountPerBuy()/100)*sp.GetStopLost())
        self.TSL = sp.GetTrailingStopLoss()
        self.Currency = sp.GetCurrency()
        self.START()

    def START(self):
        if self.Currency == "BUSD":
            self.STARTBUSD()
        elif self.Currency == "BNB":
            self.STARTBNB()
        else:
            logger.error("No Supportet Currency! Only BNB or BUSD!")

    def CalcNewTrailingStop(self, CurrentPrice):
        a = (CurrentPrice  * self.TSL) / 100
        b = CurrentPrice - a
        return b

    def STARTBUSD(self):
        try:
            balance = self.TX.get_balance_of_account()
            if balance > 0.04:
                if self.TX.fromBUSDtoToken()[0] == True:
                    HighestLastPrice = self.TX.getOutputfromTokentoBUSD()
                    StartPrice = HighestLastPrice
                    self.TrailingStopLoss = self.CalcNewTrailingStop(HighestLastPrice)
                    logger.info("Start Thread for " + self.TokenName)
                    logger.info_blue("Start Price is " + str(StartPrice))
                    logger.info_magenta("Start Stop Loss is " + str(self.TrailingStopLoss))
                    while True:
                        try:
                            time.sleep(0.5)
                            CurrentPrice = self.TX.getOutputfromTokentoBUSD()
                            if CurrentPrice > HighestLastPrice:
                                HighestLastPrice = CurrentPrice
                                TrailingStopLoss = self.CalcNewTrailingStop(CurrentPrice)
                            if CurrentPrice <= TrailingStopLoss:
                                logger.warning("[TRAILING STOP LOSS] Trigger: " + self.TokenName)
                                Result = self.TX.fromTokentoBUSD()[1]
                                if Result[0] == True:
                                    CurrentBalance = self.TX.get_balance_of_account()
                                    logger.success(Result[1] + "Current Balance is " + str(CurrentBalance))
                                else: logger.error(Result[1])
                                break
                            info_price = str(self.TokenName) + " -> Start | Current | Stop Loss: " + str(StartPrice) + str(round(CurrentPrice, 2)) + " | " + str(round(self.TrailingStopLoss, 2)) + " $"
                            logger.info(info_price)
                        except Exception as e:
                            print(e)
                            break
                else:
                    e = "Buy TX FAILD: " + str(self.TokenName)
                    logger.error(e)
            else:
                e = "Buy TX FAILD: " + str(self.TokenName)
                logger.error(e)
        except Exception as e:
            logger.error("Error while threading" + self.TokenName + " | " + self.TokenAddress)
            print(e)

    def STARTBNB(self):
        try:
            balance = self.TX.get_balance_of_account()
            if balance > 0.04:
                if self.TX.fromBNBtoToken()[0] == True:
                    HighestLastPrice = self.TX.getOutputfromTokentoBUSD()
                    self.TrailingStopLoss = self.CalcNewTrailingStop(HighestLastPrice)
                    logger.info("Start Thread for " + self.TokenName)
                    logger.info_blue("Start Price is " + str(HighestLastPrice))
                    logger.info_magenta("Start Stop Loss is " + str(self.TrailingStopLoss))
                    while True:
                        try:
                            time.sleep(0.5)
                            CurrentPrice = self.TX.getOutputfromTokentoBUSD()
                            if CurrentPrice > HighestLastPrice:
                                HighestLastPrice = CurrentPrice
                                self.TrailingStopLoss = self.CalcNewTrailingStop(CurrentPrice)
                            if CurrentPrice <= self.TrailingStopLoss:
                                logger.warning("[TRAILING STOP LOSS] Triggert: " + self.TokenName)
                                Result = self.TX.fromTokentoBNB()
                                if Result[0] == True:
                                    CurrentBalance = self.TX.get_balance_of_account()
                                    logger.success(Result[1] + " Current Balance is " + str(CurrentBalance))
                                else: logger.error(Result[1])
                                break
                            info_price = str(self.TokenName) + " Current Output | Stop Loss: " +str(round(CurrentPrice, 2)) + " $ | " + str(round(self.TrailingStopLoss, 2))
                            logger.info(info_price)
                        except Exception as e:
                            logger.error("Error while threading" + self.TokenName + " | " + self.TokenAddress)
                            print(e)
                            break
                else:
                    e = "Buy TX FAILD: " + str(self.TokenName)
                    logger.error(e)
            else:
                logger.error("Insufficient balance: " + str(balance))
        except Exception as e:
            print(e)

class TokenScrapper():

    def __init__(self):
        self.loadBlacklist()

    def ScrappTokens(self):
        logger.info_blue("Welcome to BSC Sniper bot!")
        while True:
            try:
                self.get_LastTokens()
                time.sleep(60)
            except Exception as e:
                logger.error("fetching last tokens failed!")
                print(e)


    def loadBlacklist(self):
        with open("blacklist.json","r") as e:
            self.Blacklist = json.load(e)

    def saveBlacklist(self):
      with open("blacklist.json","w") as e:
          json.dump(self.Blacklist, e)

    def get_LastTokens(self):
        current_time = dt.datetime.now()
        logger.info_blue("Fetching recently added tokens [" + str(current_time) + "]")
        url = "https://coinmarketcap.com/new/"
        base_url = "https://coinmarketcap.com"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        f = soup.find("tbody")
        all_trs = f.find_all("tr")
        binance_rows = [t for t in all_trs if t.findAll(text=re.compile("Binance"))]
        for tr in binance_rows:
            addtime = tr.find_all("td")[9].text
            if "minutes" in addtime:
                for link in tr.findAll("a"):
                    href = link.get("href")
                    token_link = urljoin(base_url, href)
                    Taddress = self.get_TokenAddress(token_link)
                    if not Taddress in self.Blacklist:
                        logger.info("Found new Token! Added " + str(addtime) + " ago | Address:" + Taddress)
                        self.Blacklist.append(Taddress), self.saveBlacklist()
                        IsHoneyPot, SELLTAX, BUYTAX = HoneyPotChecker(Taddress).getTAX()
                        MAXTAX = sp.GetMaxTokenTax()
                        logger.info_blue("Honeypot is " + str(IsHoneyPot) + " | BUYTAX is " + str(BUYTAX) + " | SELLTAX is " + str(SELLTAX))
                        if IsHoneyPot == False:
                            if float(SELLTAX) <= float(MAXTAX):
                                if float(BUYTAX) <= float(MAXTAX):
                                    T(target=TakeProfitStopLoss, args=[Taddress],).start()

    def get_TokenAddress(self, url):
      page = requests.get(url)
      soup = BeautifulSoup(page.content, "html.parser")
      h = soup.find_all("span", class_="mainChainAddress")
      parent_a = h[0].find_parent("a")
      href = parent_a.get("href")
      x = href.split("/")
      token_address = x[-1]
      return token_address

TokenScrapper().ScrappTokens()