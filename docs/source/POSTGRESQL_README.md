
# 

## PostgreSQL Setup


### set up postgresql databank

* run the following to see postgresql service status
``` 
sudo systemctl start postgresql.service
``` 
* follow steps 2 and 3 to add a new role with the same username as your linux user; [postgresql on Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-install-postgresql-on-ubuntu-20-04-quickstart)

* then create a db with name "red" as in step 4. we do not need ident based authent as in step 5.

* after this the command "psql -d red" should work.  

* let the port be accessed for DB (replace 'XY' with your postgresql version, e.g. '12')
```
cd /etc/postgresql/XY/main/
```

open file named postgresql.conf
```
sudo vi postgresql.conf
```
add this line to that file to let the postgresql server listen for connections::
```
listen_addresses = '*'
```

then open file named pg_hba.conf
```
sudo vi pg_hba.conf
```
and add this line to that file to allow access to all databases for all users with an encrypted password:
```
host  all  all 0.0.0.0/0 md5
```
 and the following line as the first line to let users connect with password not encrypted:
```
host  all  all 0.0.0.0/0 trust
```

* set password of user_name using (assuming logged in as linux user with psql account):
```
psql -d red
```
```
\password
```

* allow the DBs port (default 5432) to be accessed through the firewall

* then restart DB server: 
```
sudo service postgresql start
```

### Create PostgreSQL Schema and Tables

* go to openburst/db folder

* change OWNER username to your linux username in file create_tables.sql 

* create scheme
```
psql red -f create_schemes.sql
```
 
* then call the create tables command

```
psql red -f create_tables.sql
```

* then create triggers (openBURST uses triggers to notify processes waiting for DB changes, e.g. sensors waiting for target movements)
```
psql red -f create_triggers.sql
```

* then write table entries (check ip address hardcoded; TBD better read in correct ip address)
```
psql red -f write_table_entries.sql
```


### pgadmin to view the DB
* Install pgadmin4 (if pgadmin4 does not work with python3.10 and your Linux distribution and version, try with a lower Python version e.g. python3.8); see e.g. [pgadmin4 on Ubuntu](https://tecadmin.net/how-to-install-pgadmin4-on-ubuntu-20-04/)

* in order to view the DB open pgadmin4 and then add server above with the username and password; Hostname should be "localhost", port "5432" and maintenance database "postgres". 

* then you click through the pgadmin GUI to connect to the DB created above and view or query the tables. 