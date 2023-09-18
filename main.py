from wialon import Wialon, WialonError
import carpriceApi2 as carpriceAPI
import asyncio
from datetime import datetime, timedelta
import sys

objects={}

def delete_movement(movement_id):
    movement = carpriceAPI.updateMovement({
                        "uuid": movement_id.strip(),
                        "status": "CANCELED"
                     })
    print(movement)
    
def get_object_from_uid(uid):
    global objects
    for object in objects.values():
        if object["uid"] == uid:
            return object
            
def update_objects(object_data, uid):
    global objects
    for object in objects.values():
        if object["uid"] == uid:
            object == object_data
            return

async def run(sleep: int):
    try:
        global objects
        resources = wialon_api.core_search_items({
            "spec": {
                "itemsType": "avl_resource",
                "propName": "notifications",
                "propValueMask": "*",
                "sortType": "sys_unique_id"
            },
            "force": 1,
            "flags": 1024 + 32 + 1,
            "from": 0,
            "to": 0
        })
        resources = resources["items"][0]
        
        units = wialon_api.core_search_items({
            "spec": {
                "itemsType": "avl_unit",
                "propName": "sys_name",
                "propValueMask": "*",
                "sortType": "sys_name"
            },
            "force": 1,
            "flags": 1 + 32 + 256 + 1024 + 131072,
            "from": 0,
            "to": 0
        })
        
        result = wialon_api.core_update_data_flags({
            "spec": [{
                "type": "col",
                "data": [item["id"] for item in units["items"]] + [resources["id"]],
                "flags": 32,
                "mode": 0
            }]
        })
        
        for item in units["items"]:
            if "uid" in item:
                objects.setdefault(item["id"],
                                   {"uid": item["uid"],
                                    "name": item["nm"],
                                    "last_t" : 0,
                                    "busy" : False,
                                    "movement_id" : 0
                                    })
        print(objects)
        log_file.write(f"{datetime.now()}\n{objects}\n\n")
    except WialonError as e:
        wialon_api.core_logout()
        print("Wialon error: " + str(e))
        log_file.write(f"{datetime.now()} Wialon error: " + str(e) + "\n")
        log_file.close()
        sys.exit()

    except KeyboardInterrupt:
        wialon_api.core_logout()
        print("Aborted successfully")
        log_file.write(f"{datetime.now()} Aborted successfully\n")
        log_file.close()
        sys.exit()

    except Exception as e:
        wialon_api.core_logout()
        print("Error: " + str(e))
        print("Exit successfully")
        log_file.write(f"{datetime.now()} Error: " + str(e) + "\n")
        log_file.close()
        sys.exit()
    
    while True:
        try:
            await asyncio.sleep(sleep)
            flag = False
            for object in objects.values():
                if object["busy"]:
                    flag = True
                    print(object)
                    log_file.write(f"{object}\n")
            
            if flag:
                log_file.write("\n")
                print("")

            now = datetime.now() - timedelta(seconds=(sleep*3 + 60*60))
            waybills = carpriceAPI.findWaybills({
                "filter": {
                    "is_remote_shipment": True,
                    "status_code_in": [30, 40, 50],
                    "created_at_from": now.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            })

            waybills1 = carpriceAPI.findWaybills({
                "filter": {
                    "is_remote_shipment": True,
                    "status_code_in": [30, 40, 50],
                    "updated_at_from": now.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            })
            print("waybills:")
            print(waybills)
            print("")
            print(waybills1)
            print("")
            log_file.write(f"{datetime.now()}\nwaybills:\n{waybills}\n\n{waybills1}\n\n")

            if waybills:
                for waybill in waybills:
                    if waybill["comment"] != "":
                        print("------------------------------------------------------------Succes------------------------------------")
                        log_file.write("------------------------------------------------------------Succes------------------------------------")
                        duid = waybill["comment"].replace(" ","")
                        duid = duid[duid.find("id(")+3:duid.find(")")]
                        object = get_object_from_uid(duid)
                        if object["busy"]:
                            continue
                        movement = carpriceAPI.createMovement({
                            "duid": duid,
                            "object": {
                                "type": "waybill",
                                "id": str(waybill["id"])
                            }
                        })
                        if movement:
                            object["movement_id"] = movement["uuid"]
                            object["busy"] = True
                            print(f"For object {object['name']}, uid: {object['uid']} created movement {movement['uuid']}")
                            log_file.write(f"{datetime.now()} \nFor object {object['name']}, uid: {object['uid']} created movement {movement['uuid']}\n\n")
                        else:
                            print("Movement not created")
                            log_file.write(f"{datetime.now()} \nFor object {object['name']}, uid: {object['uid']}  movement NOT created\n\n" )
                        update_objects(object, duid)
                    
            res = wialon_api.avl_evts()
            events = res['events']
            
            for event in events:
                if event['i'] == resources['id']:
                    print(f"Event: \n{event}")
                    log_file.write(f"{datetime.now()}\n")
                    log_file.write(f"Event:\n{event}\n\n")
                    data = event['d']
                    
                    if data['tp'] == 'unm':
                        if data['name'] == 'Режим водителя':
                            response = carpriceAPI.updateMovement({
                           "uuid": objects[data["unit"]]["movement_id"],
                           "status": "STARTED"
                    })
                            print(f"For object {objects[data['unit']]['name']} movement started!\nResponse status: {response.status_code}")
                            log_file.write(f"{datetime.now()} \nFor object {objects[data['unit']]['name']} movement started!\nResponse status: {response.status_code}\n\n")
                        
                        if data['name'] == 'Пеший режим':
                            response = carpriceAPI.updateMovement({
                                "uuid": objects[data["unit"]]["movement_id"],
                                "status": "DONE"
                            })
                            if response.status_code == 200:
                                objects[data["unit"]]["busy"] = False
                                objects[data["unit"]]["movement_id"] = 0
                                print(f"For object {objects[data['unit']]['name']} movement done!\nResponse status: {response.status_code}")
                                log_file.write(f"{datetime.now()} \nFor object {objects[data['unit']]['name']} movement done!\nResponse status: {response.status_code}\n\n")
                            else:
                                print(f"For object {objects[data['unit']]['name']} movement NOT done!\nResponse status: {response.status_code}")
                                log_file.write(f"{datetime.now()} \nFor object {objects[data['unit']]['name']} movement NOT done!\nResponse status: {response.status_code}\n\n")
                            
            units = wialon_api.core_search_items({
                "spec": {
                    "itemsType": "avl_unit",
                    "propName": "sys_name",
                    "propValueMask": "*",
                    "sortType": "sys_name"
                },
                "force": 1,
                "flags": 1 + 256 + 1024 + 131072,
                "from": 0,
                "to": 0
            })

            for item in units["items"]:
                y = item["pos"]["y"]
                x = item["pos"]["x"]
                speed = item["pos"]["s"]
                uid = item["uid"]
                direction = item["pos"]["c"]
                t = item["pos"]["t"]

                # if t > objects[item["id"]]["last_t"]:

                response = carpriceAPI.add_coordinates({
                    "duid": item["uid"],
                    "coordinates": {
                        "latitude": y,
                        "longitude": x
                    },
                    "speed": speed,
                    "direction": direction
                })
                print(f"Object {item['nm']}\n"
                        f"time: {t}\n"
                        f"coordinates: {y} N    {x} E\n"
                        f"Response status: {response.status_code}\n")
                log_file.write(f"Object {item['nm']}\n"
                        f"{datetime.now()} time: {t}\n"
                        f"coordinates: {y} N    {x} E\n"
                        f"Response status: {response.status_code}\n\n")
                    # objects[item["id"]]["last_t"] = t

        except WialonError as e:
            print("Wialon error: " + str(e))
            log_file.write(f"{datetime.now()} Wialon error: " + str(e) + "\n")

        except KeyboardInterrupt:
            wialon_api.core_logout()
            print("Aborted successfully")
            log_file.write(f"{datetime.now()} Aborted successfully\n")
            log_file.close()

        except Exception as e:
            print("Error: " + str(e))
            log_file.write(f"{datetime.now()} Error: " + str(e) + "\n")



if __name__ == '__main__':
    try:
        log_file = open("log.txt", "w+")
        wialon_api = Wialon()
        result = wialon_api.token_login(
            token='0adc759ef06689a927244b5d1d6aada09D01F66F10EF61CE2E85A71DD3B6D7AB523F57DD')
        if result:
            print("Wialon connected succesfully")
            log_file.write("Wialon connected succesfully\n")
        wialon_api.sid = result['eid']
        au = result['au']
        print(carpriceAPI.tokenCarPrice)
        log_file.write(f"{carpriceAPI.tokenCarPrice}\n")
        #result = carpriceAPI.carprice_login()
#        print(result)
#        if result.status_code == 200:
#            print("Carprice connected succesfully")
#            log_file.write("Carprice connected succesfully\n")

    except WialonError as e:
        wialon_api.core_logout()
        print("Wialon error: " + str(e))
        log_file.write("Wialon error: " + str(e) + "\n")
        log_file.close()
        sys.exit()

    except KeyboardInterrupt:
        wialon_api.core_logout()
        print("Aborted successfully")
        log_file.write(f"{datetime.now()} Aborted successfully\n")
        log_file.close()

    except Exception as e:
        wialon_api.core_logout()
        print("Error: " + str(e))
        print("Exit successfully")
        log_file.write("Error: " + str(e) + "\n")
        log_file.write("Exit successfully\n")
        log_file.close()
        sys.exit()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'del_movement':
            print(sys.argv[2])
            delete_movement(sys.argv[2])
    else:     
        loop = asyncio.get_event_loop()
        print("Running...")
        log_file.write("Running...\n")
        loop.run_until_complete(loop.create_task(run(60)))
