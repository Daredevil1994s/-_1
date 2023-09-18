import ast
import json
import time
import requests

tokenCarPrice = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1OSIsInR5cCI6ImNhcnJpZXIifQ.tNAueOqZqLY40QYJVTmUkd_BOxs7IVorFt1BDFqaLe4"
login = "v.yackov@matrix-msk.ru"
password = "CarPrice2023"
timeLog = time.time()
session = requests.Session()


def carprice_login():
    global tokenCarPrice
    global timeLog
    my_headers = {'X-AUTH-CARRIER': tokenCarPrice}
    time.sleep(0.01)
    response = session.get("https://log.carprice.auction/api/v3/transfer_requests?limit=100&page=1", headers=my_headers)
    if response.status_code != 200 or time.time() - timeLog > 20 * 60 * 60:
        timeLog = time.time()
        resp = session.post(url="https://api.carprice.ru/api/authJwt.getV1",
                            data={"login": login, "password": password})
        dict_str = resp.content.decode("utf-8")
        resp_dict = ast.literal_eval(dict_str)
        #tokenCarPrice = resp_dict["tokens"][0]["token"]
        my_headers = {'X-AUTH-CARRIER': tokenCarPrice}
        time.sleep(0.01)
        response = session.get("https://log.carprice.auction/api/v3/transfer_requests?limit=100&page=1", headers=my_headers)
    return response


def findWaybills(data):
    global tokenCarPrice
    my_headers = {
        'x-token': tokenCarPrice
    }
    response = session.post("https://api.carprice.auction/movement-tracking/v1/Carrier.FindWaybills",
                            headers=my_headers, json=data)
    if response.status_code == 200:
        data_tmp = response.content.decode("utf-8")
        return json.loads(data_tmp)["waybills"]


def createMovement(data):
    global tokenCarPrice 
    my_headers = {
        'x-token': tokenCarPrice
    }
    response = session.post("https://api.carprice.auction/movement-tracking/v1/Carrier.CreateMovement",
                            headers=my_headers, json=data)
    if response.status_code == 200:
        data_tmp = response.content.decode("utf-8")
        return json.loads(data_tmp)["movement"]


def updateMovement(data):
    global tokenCarPrice
    my_headers = {
        'x-token': tokenCarPrice
    }
    response = session.post("https://api.carprice.auction/movement-tracking/v1/Carrier.UpdateMovementStatus",
                            headers=my_headers, json=data)
    return response


def add_coordinates(data):
    global tokenCarPrice
    my_headers = {
        'x-token': tokenCarPrice
    }
    response = session.post("https://api.carprice.auction/movement-tracking/v1/Carrier.AddCoordinates",
                            headers=my_headers, json=data)
    return response
