import requests
import sys

def print_help():
    print("Usage: python client.py --COMMAND DEVICE <--host IP --port PORT>")
    exit()

def parse_args(args):
    command = args[1]
    device = args[2]
    command_list = ['--record', '--stop', '--pause']
    device_list = ['zed', 'csi', 'all']
    if (len(args) >= 5 and args[3]=='--host'):
        host = args[4]
    else:
        host = "127.0.0.1"
    if (len(args) >= 7 and args[5]=='--port'):
        port = int(args[6])
    else:
        port = 8000
    if command in command_list and device in device_list:
        return command, device, host, port
    else:
        print_help()


def main():
    if (sys.argv is None or len(sys.argv)< 3):
        print_help()
        return
    command, device, host, port = parse_args(sys.argv)
    url = "http://"+host+":"+str(port)+"/"+command[2:]
    timeout = 2
    payload = {'device': device}
    r = requests.get(url, timeout=timeout, params=payload)
    print(r.url)

if __name__=="__main__":
    main()