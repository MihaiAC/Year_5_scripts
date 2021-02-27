import subprocess
import time
import os
import signal
import filecmp

# cmd = ['python3', 'some_script.py']
# result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
# print(result.stdout.read().decode('utf-8') + "!!!!!")

def kill_process_group(subprocess):
    os.killpg(os.getpgid(subprocess.pid), signal.SIGTERM)

def check_identical_files():
    return filecmp.cmp("test.jpg", "new_test.jpg", shallow=False)

def extract_numbers(output_string):
    str_numbers = output_string.split()
    numbers = [float(x) for x in str_numbers]
    return numbers

def calculate_average(ls):
    lsum = 0
    for l in ls:
        lsum += l
    return lsum/len(ls)

# Testing problem 2:
def test_p2():
    sender_instr = "python3 Sender2.py localhost 12000 test.jpg "
    for retransmission_timeout in [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]:
        curr_sender_instr = sender_instr + str(retransmission_timeout)
        retransmissions = []
        throughputs = []
        for _ in range(5):
            receiver = subprocess.Popen("python3 Receiver2.py 12000 new_test.jpg",
                            shell=True,
                            stdout=subprocess.PIPE,
                            preexec_fn=os.setsid,
                            cwd=r'/vagrant/CW2')

            sender = subprocess.Popen(curr_sender_instr,
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    preexec_fn=os.setsid,
                                    cwd=r'/vagrant/CW2')
            
            while(sender.poll() is None):
                time.sleep(1)

            start_time = time.time()
            correctly_terminated = True
            while(receiver.poll() is None):
                time.sleep(1)
                if time.time() - start_time > 10:
                    correctly_terminated = False
                    break
            
            if not correctly_terminated:
                print('Receiver did not terminate correctly.')
                return 0
            
            if not check_identical_files():
                print('Files not identical.')
                return 0
            
            sender_output = sender.stdout.read().decode('utf-8')[:-1]
            numbers = extract_numbers(sender_output)
            retransmissions.append(numbers[0])
            throughputs.append(numbers[1])
        print(str(retransmission_timeout) + 'ms:')
        avg_retransmissions = calculate_average(retransmissions)
        avg_throughputs = calculate_average(throughputs)
        print(str(avg_retransmissions) + ' ' + str(avg_throughputs))

def test_p3():
    sender_instr = "python3 Sender3.py localhost 12000 test.jpg 18 "
    for window_size in [1, 2, 4, 8, 16, 32, 64, 128, 256]:
        curr_sender_instr = sender_instr + str(window_size)
        throughputs = []
        for _ in range(5):
            receiver = subprocess.Popen("python3 Receiver3.py 12000 new_test.jpg",
                            shell=True,
                            stdout=subprocess.PIPE,
                            preexec_fn=os.setsid,
                            cwd=r'/vagrant/CW2')

            sender = subprocess.Popen(curr_sender_instr,
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    preexec_fn=os.setsid,
                                    cwd=r'/vagrant/CW2')
            
            while(sender.poll() is None):
                time.sleep(1)

            start_time = time.time()
            correctly_terminated = True
            while(receiver.poll() is None):
                time.sleep(1)
                if time.time() - start_time > 10:
                    correctly_terminated = False
                    break
            
            if not correctly_terminated:
                print('Receiver did not terminate correctly.')
                return 0
            
            if not check_identical_files():
                print('Files not identical.')
                return 0
            
            sender_output = sender.stdout.read().decode('utf-8')[:-1]
            numbers = extract_numbers(sender_output)
            throughputs.append(numbers[0])
        print(str(window_size) + ':')
        avg_throughput = calculate_average(throughputs)
        print(str(avg_throughput))

test_p3()
