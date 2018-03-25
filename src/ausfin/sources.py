import logging
from typing import List

from selenium import webdriver


from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger
selenium_logger.setLevel(logging.CRITICAL)


class Source:
    def __init__(self, implicit_wait_secs=10, driver=None):
        self.implicit_wait_secs = implicit_wait_secs
        self.driver = driver or self._driver()

        self.logger = logging.getLogger(__name__)

    def fetch_balance(self, username, password):
        self.logger.info('Fetching balance')
        balance = self._fetch_balance(username, password)

        self.logger.debug('Quitting driver')
        self.driver.quit()

        return balance

    def _fetch_balance(self, username, password, base_url=None):
        pass

    def _driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--log-level=3')
        driver = webdriver.Chrome(chrome_options=options)
        driver.implicitly_wait(time_to_wait=self.implicit_wait_secs)

        return driver

    def _balance_to_num(self, balance):
        return float(balance[1:].replace(',', '').replace(' ', ''))

class TwentyEightDegreesSource(Source):
    def _fetch_balance(self, username, password, base_url='https://28degrees-online.latitudefinancial.com.au/'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('AccessToken_Username')
        password_field = self.driver.find_element_by_id('AccessToken_Password')
        login_btn = self.driver.find_element_by_id('login-submit')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        balance_field = self.driver.find_element_by_id('current-expenses-value')

        # Negate balance as credit card = debts
        return -1 * self._balance_to_num(balance_field.text)


class UbankSource(Source):
    def _fetch_balance(self, username, password, base_url='https://www.ubank.com.au/NAGAuthn/ubank.secgate.action'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('username')
        password_field = self.driver.find_element_by_id('password')
        login_btn = self.driver.find_element_by_name('Login')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        # actual id name has a lot of strange IDs. Not sure if these change, so do a partial match
        balance_field = self.driver.find_element_by_xpath('//*[contains(@id, "uipt1:sf1:a3:itAmount::content")]')

        return self._balance_to_num(balance_field.text)


class SuncorpBankSource(Source):
    def _fetch_balance(self, username, password, base_url='https://internetbanking.suncorpbank.com.au/'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('UserId')
        password_field = self.driver.find_element_by_id('password')
        login_btn = self.driver.find_element_by_id('login-button')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        # Doesn't have a summary balance field so calculate it ourselves
        balance_table = self.driver.find_element_by_id('BalanceTable').find_element_by_tag_name('tbody')
        balance_rows = balance_table.find_elements_by_tag_name('tr')

        # table goes account name, account number, current balance, available funds, balance alerts
        balances = [self._balance_to_num(balance_row.find_elements_by_tag_name('td')[2].text)
                    for balance_row in balance_rows]

        return sum(balances)


class KeypadButton:
    def __init__(self, data):
        self.text = None
        self.element = None
        self.data = data

    def __repr__(self):
        return f'KeypadButton(text={self.text},element={self.element})'


class IngBankSource(Source):
    # PNG data fields from one set of page loads of the keypad
    num_pad_btns = {
        '0': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAPgSURBVHhe7dyxShxRGIbhcQu9CPtcSO5BSLUiSJqgadIGvICkT5EuXSB10qYIFhYqpBJsA4rEQiHaeDLfOBNk88/uOntWZj7eHx5017NbvRzOzu5aNJM2itXzzdHu+Xi0X/68KiWgx67qVnfVbp3x/VyMi/Xyj4cTDwCGoWxXDVcxVztzHfPl1ijdbK+ku5dFSkCPqVG1qmbrqI9Odoq14mxztNPETMgYGjXbRK2Wi/ocUtUePQDoO7Vb79L72qFvdYPdGUOlduugb4rql1K0EBiKpmOChgWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWCfkrvXqT04dW9vefxGiyEoJdN8f78kcL5c53SwTfizoigl+XNs/aQJ0dhf3kfPw8ehaCXQTH/Oq1rfcQQ9cIIehl0jOg6OqJEz4m5EHRuCrJtdAT5+jGl759T+n1W3zkxuj96XsyFoHM7Pa7LnJjJnXfasYSjR2cEnZMuy0WjXTlar6j1gnBytJNH6zETQeeko0Q0CjdaL23n7WgtZiLonKIjxKzd9tPbeuHE8OKwE4LOKZq240ZDu3c0sx6HEEHn0nZ1Y56dNhqC7oSgc2kLWi8Uo/UPRUcVXS2J1mIqgs5FO2o00dpJ0aU+gu6EoHMh6F4g6FwIuhcIOheC7gWCzoWge4Ggc1kk6OiDSnrXMVqLqQg6F65D9wJB59I16LYPNOkt8Wg9piLonKKZtdPqo6LR8D3DTgg6p+gdP90XrW1E3zvkQ/6dEXRObR8fbdttdX80vCDsjKBzajsPa5eOPhMdXa7TcNzojKBza4tUUeu8rBeJ+hkdTzT6wH/0vJgLQefWtkvPM/o6FrvzQgh6GdquXMwaLtUtjKCX5TFR85+TsiHoZdJ5ue1M3Qz/2y4rgn4KClbHCb3J0lDs074Njk4IGlYIGlYIGlYIGlYIGlYIGlYIGlYIGsOwF9wXIGhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhY+Rf02eboVr/cBYuAIVC7ddBXxfl4tK8bN9sr4WKg79RuFXTZso4cu7pxucUujeFRs2q3CrpsuTjZKdbKso+aqFU7YaPv1KhafRDzsVouNBfjYr2M+rD+AzAs5YashquYm0kbxWr5h9fli8SDctH1fw8C+uW6arVsVu3eV1wUfwGlbXvWLa8bmgAAAABJRU5ErkJggg==',
        '1': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAM3SURBVHhe7dyxattQFIfxGw3JQ2Tvg/QdAp1sAqFLsbt0LeQB2r1Dt26Fzu3ayUOGJGugD2ATmsGGOktu75Gl1jg3OHGkg/TnO/Ajlixp+rjIJnKoJx6F/dmwGM8GxST9nScR6LB51erY2q0yXs31IBymN883TgD6IbVrDZcxlytzFfPNcRGXJ3vx7nWIEegwa9RatWarqC+uRuEgTIfFqI6ZkNE31mwdtbUcqvuQsvbcCUDXWbvVKj2xFfrWNlid0VfWbhX0MpQvktyBQF/UHRM0JBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBC0pw+vYvz5NcZfl/+dvswfi50QtIdvH1fx5ubTm/w52AlBt8lC/j2tyn1gCLpRBN20dy9i/P55e8j1EHSjCLpJdo/8Z1GV+sgh6EYRdJPsA95Th6AbRdBNy334s3327UZuCLpRBN00C7Sesx+r25DN/etD0I0i6DZ8eX//+2WCdkHQXgjaBUF7IWgXBO2FoF0QtBeCdkHQXgjaBUF7IWgXBO2FoF0QtBeCdkHQXgjaBUF7IWgXBO2FoF0QtBeCdkHQXgjaBUF7IWgXBO2FoF0QdBvsn/ot1HX24GxubP/msfagbe662Iqg2/DUB2U3x37+IHddbEXQbXju2Kqduy62Iug2PHcIemcE3YbH/sjMQ2PPJOaui60IGlL8gz7N7AMa4h800CKChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChpR/QU+Hxa29uMscBPSBtVsFPQ+zQTGxjeXJXvZgoOus3TLo1LLdcoxt4+aYVRr9Y81au2XQqeVwNQoHqeyLOmqrnbDRddaotboW86W1HGyuB+EwRX1evQH0S1qQreEy5nriUdhPb7xNHxLP0kGLeycB3bIoW03NWrurikP4C0tw0zbqOK1MAAAAAElFTkSuQmCC',
        '2': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAOvSURBVHhe7dsxS9xgHMfxxxv0Rbj3hfQ9CJ1OBOlStEvXgi+g3Tt061bo3K4dioODCp0E14IidVCoLj7NL5eUIz6hOZNcLj++f/hQr5fL9PXhSS6GcuJWWL/cnuxfTieH2b83mQissJui1X21W2Q8m6tp2MzePK58ABiHrF01nMecr8xFzNc7k3i3uxYfXoYYgRWmRtWqmi2iPjnbCxvhYnuyV8ZMyBgbNVtGrZZDsQ/Ja099AFh1ardYpQ+1Qt/rBaszxkrtFkHfhfyHTOpAYCzKjgkaFggaVggaVggaVggaVggaVggaVggaVggaVggaVoYL+iDxf0BLwwUN9ICgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgl+Xdixg/vJrRz6lj0BpB9+XNsxi/vI/x/DTWzs8fs8BTn8eTEHQfvn6M8c9tUW2DOfo2+wVInQsLIeguKcpf50WlC45W69Q5sRCC7tLB86LOJ462KKnzojGC7ppW2upoH61tiKTeL+f3RfqcaIygu6ZVutw/K2C9rh6juxx1e2zugLRC0H3QnYtUyPO0vUiNfglSx6MRgh6KLiBTQ9CtEPSQUkPQrRD0UFihe0HQQ/n0tii4MlwUtkLQQ9G3g9XRnY/UsWiMoIdQ9wUM243WCHoIqQeWtDrzPEdrBL1sWoVTw+rcCYJeprpvCPVAU+p4LIygl0XbCT2rUR0Fzp2NzhD0stQ96M8Tdp0i6GX4/rmotzK6dZc6Hk9G0H2rewhJK3bqeLRC0H3S3jg1ugjkFl0vCLov889Fzw/3m3tF0H1QsKm/LeSORu8Iug91f2ZFzL0j6K7VfROo1VkXgv+jOyKp86IRgu5S3UXgIqOoU+dGIwTdpbpbdIsMQbdC0F2q224sMgTdCkF3iRV6cAQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNK/+Cvtie3OuHh8RBwBio3SLom3A5nRzqxd3uWvJgYNWp3TzorGVtOfb14nqHVRrjo2bVbh501nI42wsbWdknZdSqnbCx6tSoWp2L+VQtB83VNGxmUR8XbwDjki3IajiPuZy4FdazN15nF4lH2UG3jz4ErJbbvNWsWbU7qziEv7tA+ppiVxUwAAAAAElFTkSuQmCC',
        '3': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAPXSURBVHhe7dyxShxBAMbx8Qp9CPs8SN5BSHUiSJqgadIGfICkT5EuXSB10qYIFhYqpBJsA4rEQiHaONlv3U2Oy6zOubvu3Zf/wA89b3arP8Pc7p6hHnEtLJ+uj7ZPx6Pd4udFIQJz7KJqdVvtVhnfjrNxWC3e3J86AFgMRbtquIy5XJmrmM83RvFqcynePA8xAnNMjapVNVtFfXC0FVbCyfpoq46ZkLFo1GwdtVoO1T6krD11ADDv1G61Su9qhb7WC1ZnLCq1WwV9FcpfCqmJwKKoOyZoWCBoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCHox/DqSYzvXvy18zQ9D60RdF/ePIvx68cYf57E5Ph1GePeF+LuGEF3TYEeH1bVZo5Pb9PnwswIumuf31eVzjh0XOp8mAlBd00r9EOHtimpcyIbQfdBe+N6fP92u6WoPxBqX639c2pobup8yEbQfdBVDW0h9DP1vlbipqhT85GNoIfStNfWKp6ajywEPRSFmxoE3QpBD4Wge0HQQ9GHw+mhfXVqLrIR9BCaPhQq8tR8ZCPox6TtRNNlux/HzVdFkI2g+/ThdVXrPUMx80xHJwi6Tzm3wXUTJnUsHoSg+5T7XIeiZrvRCYLuk2555w7tq3mWozWC7tP0g/1asbUaN9321l46dR5kI+ghKHTFmxo8G90KQQ9FUadWan05IDUfWQh6SJOPmU6O1FxkIeghNV0FSc1FFoIeUup5Do3UXGQh6KFoD536RjhXOloh6K5pXyx33cpWzE37Z/09dQyyEHSXdK15cmi11T55+lp00//q0NCc1LmRhaC7pC+5thlcsmuNoLvUZuiatLYiqfMiG0F3SduJptvadw0eH+0MQXdNq+x9++R6KGRudXeKoPukVbf+IDhJf2NF7gVBwwpBwwpBwwpBwwpBw4pv0DuJv8Geb9D4LxE0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rPwJ+mR9dK1fbhKTgEWgdqugL8LpeLSrF1ebS8nJwLxTu2XQRcvacmzrxfkGqzQWj5pVu2XQRcvhaCusFGUf1FGrdsLGvFOjanUi5kO1HDTOxmG1iHq/egNYLMWCrIbLmOsR18Jy8cbL4kPiXjHp8p+DgPlyWbZaNKt2bysO4Td5PwaE+ZHC9gAAAABJRU5ErkJggg==',
        '4': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAN8SURBVHhe7dsxTxRBGIfx4Qr4EPR+EL8DidUREmJjwMbWhA+gvYWdnYm1thaGggJIrEhoTe5CpIBEaFjnXWbNubwYvJlld/953uQXOW4uNo+Tnb01NFNthNX55mR3Pp3sxz8vogoYsIvU6q61mzK+nbNpWI9vHrY+AIxDbNcarmOud+YU8/nWpLraXqlunoeqAgbMGrVWrdkU9dHJTlgLs83JThMzIWNsrNkmams5pOuQunbvA8DQWbtpl963HfraXrA7Y6ys3RT0Vah/iLyFwFg0HRM0JBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pPQT9J7zO6CAfoIGOkLQkELQkELQkELQkELQkELQkELQj+XgS1WdHv/t3Qt/LZZG0I/hw+vKnb2n/nosjaAfw/dvqeCFsR3aW4ssBN0124W9+fTWX48sBN21z+9TwQvz69Jfi2wE3TWLtz0WubcW2Qi6S3ZZ4Q2Hwc4QdJfs4NceOyB6a1EEQXflvsMg9547RdBd+foxFbwwP2f+WhRD0F3hMNgLgu7CfYfBV0/89SiGoLvgHQbtWY7FNfZ1uO3YDftHwN2PbARd2ptnqeDW2O8X13nDJUk2gi7NduL2/Di9u84bgs5G0CXZNbJ3GPSe2/CGoLMRdEneYdAC9w6D3hB0NoIuyS4t2mP3o7213hB0NoIu5b7D4LLDE3lLIehSbHctPd7fg38i6FIIehAIuhSCHgSCLsW++Wv+N/dDeGMPLzXvt79ZxIMQdF+84S5HNoLuizcEnY2g++INQWcj6L54Q9DZCLov3hB0NoLui93RaI/3EBP+C0FDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDyp+gZ5uTa/vhxlkEjIG1m4K+CPPpZN9eXG2vuIuBobN266Bjy3bJsWsvzrfYpTE+1qy1WwcdWw4nO2Etln3URG21EzaGzhq1VhdiPraWg83ZNKzHqA/TG8C4xA3ZGq5jbqbaCKvxjZfxkHgQF13e+RAwLJd1q7FZa/e24hB+A8jP8ETGs1otAAAAAElFTkSuQmC',
        '5': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAOGSURBVHhe7dqxTttQGIbhQwa4CPZeSO8BqVMQEupSQZeulbiAdu/QrVulzu3KlIEBWJFYK4FQGUAqLLjnc+wqoifgOD51/On9pUeNie3p7ZFjO9RTbIX1y+3R/uV4NIn/3kQFsMJuqlb31W6V8XSuxmEzfnn86ABgGGK7ariMuVyZq5ivd0bF3e5a8fA6FAWwwtSoWlWzVdQnZ3thI1xsj/bqmAkZQ6Nm66jVcqiuQ8raUwcAq07tVqv0RCv0vTZYnTFUarcK+i6UH6LUjsBQ1B0TNCwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwMK+iDxN+AGcMKGngGQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQefw/XNRnJ+28+5F+pxohKBzUJht59Ob9DnRCEHnQNC9IegcCLo3BJ3DMkEfvEyfE40QdA6poFl5/wuCzoGge0PQORB0bwg6B4LuDUHnQNC9IegcUkEf/Zg+QawReBYEnUMq6Hmj0LlV1xmCzmGRoDW/b4vi28f0ubAQgs5h0aDr+fI+fT40RtA5zAb983y6Lfr81Gil5m27pRB0DromnnddrGD1o1DxpkbfpY5DIwTdlw+vqoIfza+L9P5ohKD7pDscqeGyozWC7pPubKSGe9StEXSfFG5qCLo1gu4TQXeOoPukOxqp4Rq6NYLui6LVHY3Hw12OpRB01w6/Th+iPPV+hmKed4dDx6eOQSME3SVFPDt6Mli/WVfTdmplrocXlZZC0F2at+o2HZ4SLo2gu/TUyvvc6D9D6pxYCEF3SZcUbaLmurkzBJ2DngA+92adRquy3ulInQOtEHRO+oFX/xCcpb+l9sfSCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpW/gZ9sT2614eHxE7AEKjdKuibcDkeTbRxt7uW3BlYdWq3DDq2rEuOfW1c77BKY3jUrNotg44th7O9sBHLPqmjVu2EjVWnRtXqTMynajlorsZhM0Z9XH0BDEtckNVwGXM9xVZYj1+8jT8Sj+JOt/8cBKyW27LV2KzanVYcwh+mrxqi1nBysQAAAABJRU5ErkJggg==',
        '6': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAPzSURBVHhe7duxThRdHIbxwxZwEfReiPdAYgUhITYGbGxNuADtLezsTKy1tTAUFEBiRUJrAiFSQCI0jPMuM7pZ/7PszpzB3ZfnJL98y+7ZrZ7v5MyZMdWjWEvLZxuDnbP1wV7538tSAcyxy6rVHbVbZXw3ztfTavnhwdgXgMVQtquGhzEPV+Yq5ovNQXG9tVTcPk9FAcwxNapW1WwV9eHxdlpJpxuD7TpmQsaiUbN11Go5VfuQYe3RF4B5p3arVXpPK/SN/mB1xqJSu1XQ12n4ohRNBBZF3TFBwwJBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBw4pX0LvBe3hUvILGo0fQsELQsELQsELQsELQ/8O7F3+9ehLPQSsE/VA+vS2KHydFOH6eFsXn98SdAUH37c2z5pDHx6+ru1U7+h1MhaD7pJgV6SxDK3X0W5gKQfelTcyaz7ajE4LuS9M2Q+9rFa4vCvW6nsvq3BlB90EXgNHY/xLPF63o0fuYCUH3QacW40OrcDQXWRF0bh9eVwWPDb0fzUdWBJ2bthXjQxd70VxkR9C5RScbk/bOyIqgc9KFXTRGTy/qk40aN1KyIuicJu2fFW/TubTe1+ecQXdG0DkpymhEpx7R0EkIUXdC0Dl9/ViV2WFwvNcJQed0clRV2XFopY9+H/ci6Jyagq4fDx29G6jX379VE8aG5o/+LqZG0DlFQd+3hWj6n4Bb4a0QdE5RnHovmltrOhnR8yDRfExE0Dm1CVqiwT66FYLOKTrlmGY/HA2CboWgc2o6h47mjooGQbdC0DnpNnY0Jj1p1/Qdbom3QtA56S5fNCY9nBQ9nafBHcNWCDq3WY7hmh5m4um81gg6t6Z/fqUHkOqjOK2+et30sBLbjdYIug9Nq/Q0Qycl0W9iKgTdB20lmlbfSYMHkzoj6L7MGrX2zVwIdkbQfVKgCnVS2FqV2TNnQ9APRdHqZklNF4W7T+O5aI2gYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYeVP0Kcbgxu9uA0mAYtA7VZBX6az9cGe/rjeWgonA/NO7Q6DLlvWlmNHf1xsskpj8ahZtTsMumw5HW+nlbLswzpq1U7YmHdqVK2OxHyklpPG+XpaLaM+qD4AFku5IKvhYcz1KNbScvnBy/Iicb+cdPXPl4D5cjVstWxW7d5VnNJvStllspBxMtQAAAAASUVORK5CYII=',
        '7': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAN0SURBVHhe7dsxS1tRGIfxYwb9EO79IP0OQqeIIF1K7NK14Ado9w7duhU6t6tDcXBQoZPgWohIHRSqi6fnvZ60IX2jxpxzb/LneeGHxpzo8nC4yT2G0cSNsHq22ds56/f209fLJAIL7DK3umPt5ozv5rwf1tOThxMvAJZDatcabmJuduYc88VWL15vr8TblyFGYIFZo9aqNZujPjoZhLUw3OwNRjETMpaNNTuK2loO+Tqkqd17AbDorN28S+/bDn1jD9idsays3Rz0dWi+SbyFwLIYdUzQkEDQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQJe0+j/H0eH4/vsf45pn/N3Avgi7pw6tYbOx3eX8D9yLokgi6cwRdUsmgueR4EoIu6d2LXOOc8/PU//14EEF37dcwVzw2X977a/Eggu7Sp7e54LH5fcXlxhwIukv2Ed3kHHzz1+JRCLor06637efeejwKQXfFduLJsR3bW4tHI+gu2DWyN7wZnBtBd+Hrx1zw2NibQW8tZkLQXbB4J8ci99ZiJgTdNrus8MYONnnrMROCbpt3I8VO13lrMTOCbtO0sx4cRCqGoNvk3UixHdtbiych6LbYNbI3vBksiqDb4t1I4dxGcQTdBovW+6iOcxvFEXQbvBspNpzbKI6g2+B9VMch/ioIurZpN1I4t1EFQddmO/HkcG6jGoKuadqNlL3P/nrMjaBrslva3nBuoxqCrmXajRTObVRF0LXYZYU39o+x3noUQdC1eB/V8S9W1RE0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pPwNerjZu7Fvbp1FwDKwdnPQl+Gs39u3B9fbK+5iYNFZu03QqWW75NixBxdb7NJYPtastdsEnVoOJ4Owlso+GkVttRM2Fp01aq2OxXxsLQeb835YT1Ef5ieAIuLuvzdrVaUN2RpuYh5N3Air6YnX6U3iQVp09d+LgMVy1bSamrV27yoO4Q94hbaeggnUCAAAAABJRU5ErkJggg==',
        '8': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAQNSURBVHhe7duxShxRGIbhcQu9CPtcSO5BSLUiSJqgadIGvICkT5EuXSB10qYIFhYqpBJsA4rEQiHaOJlvnUmW9T/u7OwZ2f14f3iIurNTvRzOntkUzZQbxer55mD3fDjYr/69qpTAAruqW91Vu3XG93MxLNarFw8n3gAsh6pdNTyKebQy1zFfbg3Km+2V8u5lUZbAAlOjalXN1lEfnewUa8XZ5mCniZmQsWzUbBO1Wi7qfcio9ugNwKJTu/Uqva8V+la/sDpjWandOuibYvRDJboQWBZNxwQNCwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwSNp7cX/C0TgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgn5Ke8/L8sOr/6JrMBeC7psiPvhWlr/PynB+nZbl149l+eZZ/H7MhKD7pFDbjoJ/9yK+D1oj6L5oVZ51/lwT9ZwIug+f3taFdhhtQaJ7ohWC7kNqv6wtSHONoteKHI1eG78fWiPo3LRliGY85mnXfv/88Fq0QtC5pT4Ipk4xtMWYnNPj+FpMRdC5pYKOrhXFOzkE3RlB55YKOrUvjvbRbDk6I+jcUicc2lpMbjtS8fMUsTOCzk1PBlOj048mVn0gjFbnnz8e3hOtEXQfpj1U0R45ijlaxTETgu6DVunUGXNqtDIT89wIui/aWrSNmpU5G4Luk04r2o7i58Pg3Ai6D1pto/PlNvPlfXxPtELQuSnm6Omf/qYjvTah8427zgg6tyjYyT2ythaPha3Xxu+J1gg6J20XotGpR3R96sGKJvUePIqgc9LR2+RMW21TUbOX7oSgc4qO6RRsdG1DW5Fopr0PIYLOKZo2YUZD0J0QdE7RTNty6ANiNATdCUHnFB3XaVL74dQRn4aju04IOietqqnRSq2wtSKLniKmHo3rW3nR/TEVQeekFXfWLyVFw3+S7Yygc0t9wb/t6Kun0X3RCkH3QVF3Wan5IDg3gu6Lth8KdFrYel2rMk8GsyDop6ATC30gVOAN/c5JRnYEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSv/gj7bHNzqh7vgImAZqN066KvifDjY1y832yvhxcCiU7ujoKuWteXY1S+XW6zSWD5qVu2Ogq5aLk52irWq7KMmatVO2Fh0alStjsV8rJYLzcWwWK+iPqxfAJZLtSCr4VHMzZQbxWr1wuvqQ+JBddH1gzcBi+V61GrVrNq9r7go/gKUcKnLxazZhgAAAABJRU5ErkJggg==',
        '9': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAP7SURBVHhe7dy9ThRRHIbxwxZwEfReiPdAYgUhITYGbGxNuADtLezsTKy1tTAUFEBiRUJrAiFSQCI0jPMuM0rW/+zszp5xd988J/kFlj2z1ePJmY811aPYSKsXW4O9i83BQfnzulQAC+y6anVP7VYZP4zLzbRevnk0cgCwHMp21fAw5uHKXMV8tT0obndWivvnqSiABaZG1aqaraI+Pt1Na+l8a7Bbx0zIWDZqto5aLadqHzKsPToAWHRqt1qlD7RC3+kFqzOWldqtgr5Nw19K0URgWdQdEzQsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEPT/8upJUbx78ZdeR/MwE4Luk6L9/L4ofp4X4dDf9T5xZ0PQffnwuih+3VTltgzN+/Q2/hxMhaD7oDi7DKKeGUHn9uZZVWfHoeOjz8VECDq3s5OqzJHx4+xhBdYJoX7qdTR0fPS5mAhB56RYo/H9Wzy/KX5W6c4IOqevH6siR0bTVYz9p9WEkaErH9F8tCLonKJtRNPqXIuOYdvRGUHnFI221bZpVY/mohVB5xSNtqD1fjSiuWhF0DlF4/BLPLfWdCKpv0fzMRZB5xTth3UXcNytbYLOiqBzatoPa5WOotZVDp00RoOgOyHonJouw2lopVbY2jMr/KYbK/Ug6E4IOremVXraQdCdEHQftBLPOrhb2AlB90Vbi7bHRxV+05N50WeiFUH3SSeCClbh6u6f6CRQsWu/rTnRdWj9Qxj9LEyEoOct2nNz67szgp636Ik7RR7NRSuCnidtSaKhr29F89GKoOcpOiFk/zwTgp6n6NvgOoGM5mIiBD0vTdequaEyE4Lug6LUULTaDz9+jkOvoxNBjbYvA6AVQfeh6T+WGTe0d66vTaMzgs5NK3CXwZWNLAg6t2mD1srMvjkbgu6Dtg7aP497lkPvac64h/8xNYLum1ZfPa/xGCtybwgaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVgh6WvvB37AwCBpW/gR9vjW40y/3wSRgGajdKujrdLE5ONCL252VcDKw6NTuMOiyZW059vTiaptVGstHzardYdBly+l0N62VZR/XUat2wsaiU6Nq9VHMJ2o5aVxupvUy6qPqDWC5lAuyGh7GXI9iI62Wb7wsTxIPy0k3/xwELJabYatls2r3oeKUfgN5mGB2BUP+xQAAAABJRU5ErkJggg==',
    }

    def _fetch_balance(self, username, password, base_url='https://www.ing.com.au/securebanking/'):
        self.driver.get(base_url)

        client_number_field = self.driver.find_element_by_id('cifField')
        login_btn = self.driver.find_element_by_id('login-btn')

        client_number_field.send_keys(username)

        # Keypad positions are randomised, we have to find which order the butotns are in
        keypad = self._keypad()

        # Press all the correct key pad numbers based off what we just calculated
        for character in password:
            keypad[character].click()

        login_btn.click()

        balance_field = self.driver.find_element_by_xpath('//*[@id="summary-container"]/div[3]/div/div/div/div[2]/span')
        return self._balance_to_num(balance_field.text)

    def _keypad(self):
        keypad = self.driver.find_element_by_id('keypad')
        keypad_buttons = keypad.find_elements_by_xpath('//*[@id="keypad"]/div/div/div')

        buttons = []
        for keypad_button in keypad_buttons:
            data = keypad_button.find_element_by_tag_name('img').get_attribute('src')[22:]
            button = self._button_by_data(data, buttons)
            if button is None:
                button = KeypadButton(data=data)
                buttons.append(button)
            button.element = keypad_button

        for button in buttons:
            self._set_button_value(button)

        return {key.text: key.element for key in keypad_buttons}

    def _button_by_data(self, data: str, buttons: List[KeypadButton]):
        for button in buttons:
            if button.data == data:
                return button
        return None

    def _set_button_value(self, button: KeypadButton):
        # the exact value of the png data seems to change between page loads, but the general
        # relative length of the fields stays the same. As long as the fields are relatively the
        # same length then we can guess which number they are
        closest_val = None
        closest_diff = 20
        for k, v in self.num_pad_btns.items():
            length_diff = abs(len(v) - len(button.data))
            if length_diff < closest_diff:
                closest_val = k
                closest_diff = length_diff

        button.text = closest_val


class CommbankBankSource(Source):
    def _fetch_balance(self, username, password, base_url='https://www.my.commbank.com.au/netbank/Logon/Logon.aspx'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('txtMyClientNumber_field')
        password_field = self.driver.find_element_by_id('txtMyPassword_field')
        login_btn = self.driver.find_element_by_id('btnLogon_field')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        # Provides a table with both commsec data and netbank data - we need to separate the two
        balance_table = self.driver.find_element_by_id('MyPortfolioGrid1_a').find_element_by_tag_name('tbody')
        # skip last row it's a summary row
        balance_rows = balance_table.find_elements_by_tag_name('tr')[:-1]

        total_balance = 0

        # table goes account name, account number, current balance, available funds, balance alerts
        for balance_row in balance_rows:
            cells = balance_row.find_elements_by_tag_name('td')
            nickname = cells[0].text
            bsb = cells[1].text
            acc = cells[2].text
            balance = cells[3].text
            available_funds = cells[4].text

            # commsec acocunts show this instead of a bsb
            is_bank_acc = bsb != 'View in Portfolio'

            balance_is_credit = balance[0] == '+'
            balance_num = self._balance_to_num(balance[1:])
            balance_num = balance_num * -1 if not balance_is_credit else balance_num

            if is_bank_acc:
                total_balance += balance_num

        return total_balance


class CommbankSharesSource(Source):
    def _fetch_balance(self, username, password, base_url='https://www.my.commbank.com.au/netbank/Logon/Logon.aspx'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('txtMyClientNumber_field')
        password_field = self.driver.find_element_by_id('txtMyPassword_field')
        login_btn = self.driver.find_element_by_id('btnLogon_field')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        balance_table = self.driver.find_element_by_id('MyPortfolioGrid1_a').find_element_by_tag_name('tbody')
        # skip last row it's a summary row
        balance_rows = balance_table.find_elements_by_tag_name('tr')[:-1]

        total_balance = 0

        # table goes account name, account number, current balance, available funds, balance alerts
        for balance_row in balance_rows:
            cells = balance_row.find_elements_by_tag_name('td')
            nickname = cells[0].text
            bsb = cells[1].text
            acc = cells[2].text
            balance = cells[3].text
            available_funds = cells[4].text

            # commsec acocunts show this instead of a bsb
            is_bank_acc = bsb != 'View in Portfolio'

            balance_is_credit = balance[0] == '+'
            balance_num = self._balance_to_num(balance[1:])
            balance_num = balance_num * -1 if not balance_is_credit else balance_num

            if not is_bank_acc:
                total_balance += balance_num

        return total_balance


class RatesetterSource(Source):
    def _fetch_balance(self, username, password, base_url='https://members.ratesetter.com.au/login.aspx'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('ctl00_cphContentArea_cphForm_txtEmail')
        password_field = self.driver.find_element_by_id('ctl00_cphContentArea_cphForm_txtPassword')
        login_btn = self.driver.find_element_by_id('ctl00_cphContentArea_cphForm_btnLogin')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        balance_field = self.driver.find_element_by_xpath('//*[@id="ctl00_cphContentArea_cphForm_expSummary_ExpanderContent"]/div/table/tbody/tr[4]/td[2]')
        return self._balance_to_num(balance_field.text)


class AcornsSource(Source):
    def _fetch_balance(self, username, password, base_url='https://app.acornsau.com.au/auth/login'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_class_name('spec-login-email-input')
        password_field = self.driver.find_element_by_class_name('spec-login-password-input')
        login_btn = self.driver.find_element_by_class_name('spec-login-button')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        balance_field = self.driver.find_element_by_tag_name('output')

        return self._balance_to_num(balance_field.text)
