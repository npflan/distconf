import csv
import time
import config
import paramiko
import threading

# Converts csv to json(sssssh It's easier)
def make_json():
    output = {}
    with open('access.csv') as f:
        reader = csv.reader(f, delimiter=';')
        for line in reader:
            output[line[0]] = line[1]
    return output

SWTICH_DATA = make_json()

class DistPoint(threading.Thread):
    def __init__(self,dist_ip):
        threading.Thread.__init__(self)
        self.dist_ip = dist_ip
    def generate_config(self,dist):
        '''
        Generate commands for configuring dist point trunk ports
        '''
        conf = ['conf t']
        data = self.execute_ssh_command(config.username,config.password,dist,['sh cdp nei'])
        for item in data['sh cdp nei'].split('\r\n'):
            name = item.split('.')
            port = item[17:25]
            if name[0] in SWTICH_DATA.keys():
                conf.append('interface ' + port)
                conf.append('switchport trunk encapsulation dot1q')
                conf.append('switchport mode trunk')
                conf.append('switchport trunk native vlan ' + SWTICH_DATA[name[0]])
                conf.append('switchport trunk allowed vlan 193,' + SWTICH_DATA[name[0]])
        conf.append('do wr')
        return conf
    def execute_ssh_command(self,username,password,host,commands):
        cmd_output = {}
        client_pre = paramiko.SSHClient()
        client_pre.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #Try to connect to device
        try:
            client_pre.connect(host, username=username, password=password)
        except:
            #Returns authentication error if connection fails
            for command in commands:
                cmd_output[command] = 'Authentication error '
            return cmd_output
        # Creates 'live' access to the switch console. Enables execution of multiple commands per login
        client = client_pre.invoke_shell()
        # Removes Max length of the terminal. Basically it removes the --more--.
        client.send("term len 0\n")
        output = ''
        #Waits untill the last character is '#', in the console output
        while not output.strip().endswith('#'):
            time.sleep(.1)
            output = client.recv(65535).decode("utf-8")
        #Executes commands one by one
        for command in commands:
            output = ''
            client.send(command + "\n")
            #Waits untill the last character is '#', in the console output
            while not output.strip().endswith('#'):
                time.sleep(.1)
                output = output + client.recv(65535).decode("utf-8")
            #Adds the output the cmd_output dict, where the key is the command
            cmd_output[command] = output
        client.close()
        client_pre.close()
        return cmd_output
    def push_config(self,dist,commands):
        self.execute_ssh_command(config.username,config.password,dist,commands)
    def run(self):
        data = self.generate_config(self.dist_ip)
        self.push_config(self.dist_ip,data)
# Start a thread for each dist point(gotta go fast)
for line in config.dist_sw:
    thread = DistPoint(line)
    thread.start()