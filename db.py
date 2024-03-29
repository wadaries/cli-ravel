#/usr/bin/env python

import psycopg2

ISOLEVEL = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT

class RavelDb():
    def __init__(self, name, user):
        self.dbname = name
        self.user = user
        self.truncate()
        self.create()
        self.add_extensions()
        
    @property
    def name(self):
        return self.dbname
        
    def connect(self, db=None):
        if db is None:
            db = self.name

        conn = psycopg2.connect(database=db,
                                    user=self.user)
        conn.set_isolation_level(ISOLEVEL)
        return conn

    def fmt_errmsg(self, exception):
        return str(exception).strip()

    def load_schema(self, script):
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            s = open(script, 'r').read()
            cursor.execute(s)
        except psycopg2.DatabaseError, e:
            print "error loading schema:", self.fmt_errmsg(e)

        finally:
            if conn:
                conn.close()

    def load_topo(self, topo, net):
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()

            switches = {}
            for sw in topo.switches():
                # TODO: better naming scheme
                name = sw.replace("s", "")
                dpid = net.getNodeByName(sw).defaultDpid()
                ip = net.getNodeByName(sw).IP()
                switches[sw] = name
                cursor.execute("INSERT INTO switches VALUES ({0});".format(name))

            hosts = {}
            for host in topo.hosts():
                # TODO: better naming scheme
                name = int(host.replace("h", "")) + len(topo.switches())
                ip = net.getNodeByName(host).IP()
                mac = net.getNodeByName(host).MAC()
                hosts[host] = name
                cursor.execute("INSERT INTO hosts VALUES ({0}, '{1}', '{2}');"
                               .format(name, ip, mac))

            nodes = {}
            nodes.update(hosts)
            nodes.update(switches)
            for link in topo.links():
                h1,h2 = link
                if h1 in switches and h2 in switches:
                    ishost = 0
                else:
                    ishost = 1
                
                sid = nodes[h1]
                nid = nodes[h2]
                cursor.execute("INSERT INTO tp(sid, nid, ishost, isactive) "
                               "VALUES ({0}, {1}, {2}, {3});"
                               .format(sid, nid, ishost, 1))

        except psycopg2.DatabaseError, e:
            print e
        finally:
            if conn:
                conn.close()

    def create(self):
        conn = None
        try:
            conn = self.connect("postgres")
            cursor = conn.cursor()
            cursor.execute("SELECT datname FROM pg_database WHERE " +
                           "datistemplate = false;")
            fetch = cursor.fetchall()
            
            dblist = [fetch[i][0] for i in range(len(fetch))]
            if self.name not in dblist:
                cursor.execute("CREATE DATABASE %s;" % self.name)
        except psycopg2.DatabaseError, e:
            print "error creating database:", self.fmt_errmsg(e)
        finally:
            if conn:
                conn.close()

    def add_extensions(self):
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM pg_catalog.pg_namespace n JOIN " +
                           "pg_catalog.pg_proc p ON pronamespace = n.oid " +
                           "WHERE proname = 'pgr_dijkstra';")
            fetch = cursor.fetchall()
            if fetch == []:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS plpythonu;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pgrouting;")
                cursor.execute("CREATE EXTENSION plsh;")
        except psycopg2.DatabaseError, e:
            print "error loading extensions:", self.fmt_errmsg(e)
        finally:
            if conn:
                conn.close()
            
    def query(self, qry):
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(qry)
            fetch = cursor.fetchall()
            return fetch
        except psycopg2.DatabaseError, e:
            print "error executing query:", self.fmt_errmsg(e)
        finally:
            if conn:
                conn.close()

    def clean(self):
        conn = None
        try:
            conn = self.connect("postgres")
            cursor = conn.cursor()
            cursor.execute("drop database %s" % self.name)
        except psycopg2.DatabaseError, e:
            print "error cleaning database:", self.fmt_errmsg(e)
        finally:
            if conn:
                conn.close()

    def truncate(self):
        conn = None
        try:
            # TODO: add ports to tables
            # TODO: also add hosts, switches?
            tables = ["cf", "clock", "p1", "p2", "p3", "p_spv", "pox_hosts", 
                      "pox_switches", "pox_tp", "rtm", "rtm_clock",
                      "spatial_ref_sys", "spv_tb_del", "spv_tb_ins", "tm",
                      "tm_delta", "utm", "acl_tb", "acl_tb", "lb_tb",
                      "hosts", "switches", "tp"]
            tenants = ["t1", "t2", "t3", "tacl_tb", "tenant_hosts", "tlb_tb"]

            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("truncate %s;" % ", ".join(tables))

            cursor.execute("INSERT INTO clock values (0);")

            # TODO: fix
            #cursor.execute("truncate %s;" % ", ".join(tenants))
        except psycopg2.DatabaseError, e:
            print "error truncating databases:", self.fmt_errmsg(e)
        finally:
            if conn:
                conn.close()
