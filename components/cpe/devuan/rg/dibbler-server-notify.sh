#!/bin/bash

# This script will be called by dibbler-server with a single parameter
# describing operation (add, update, delete, expire)
# parameters add,update will cause adding a new rule in the main routing table
# and in the gw routing table (table 3) while parameters del,expire will remove
# the relevant rule from both tables.
# add/delete entries to/from the routing table is done both to the main table and to table 3
# which is the gateway's routing table. for packets going in the upstream direction , table 3 will route them to
#the correct path. for packets going to the downstream direction - the main table will route them to their destination.


LOGFILE=/var/lib/dibbler/server-notify.log

echo "---$1--------" >> $LOGFILE
date >> $LOGFILE

if [ "$ADDR1" != "" ]; then
    echo "Address ${ADDR1} (operation $1) to client $REMOTE_ADDR on inteface $IFACE/$IFINDEX" >> $LOGFILE
fi

if [ "$PREFIX1" != "" ] ; then
    if [ "$1" = "add" ] || [ "$1" = "update" ]; then
        echo "Prefix ${PREFIX1} (operation $1) to client $REMOTE_ADDR on inteface $IFACE/$IFINDEX" >> $LOGFILE
        #iproute2 doesn't detect duplicate rules, so we need to delete the rule before adding it to avoid
        #creating duplicate rules when the clients renew / rebind / update / etc.
        ip -6 rule del from ${PREFIX1}/${PREFIX1LEN} iif $IFACE lookup 3 priority 21000
        ip -6 rule add from ${PREFIX1}/${PREFIX1LEN} iif $IFACE lookup 3 priority 21000
        ip -6 route add table 3 ${PREFIX1}/${PREFIX1LEN} via $REMOTE_ADDR dev $IFACE;
        ip -6 route add ${PREFIX1}/${PREFIX1LEN} via $REMOTE_ADDR dev $IFACE;
    fi

    if [ "$1" = "del" ] || [ "$1" = "expire" ]; then
        echo "Prefix ${PREFIX1} (operation $1) to client $REMOTE_ADDR on inteface $IFACE/$IFINDEX" >> $LOGFILE
        ip -6 rule del from ${PREFIX1}/${PREFIX1LEN} iif $IFACE lookup 3 priority 21000
        ip -6 route del table 3 ${PREFIX1}/${PREFIX1LEN} via $REMOTE_ADDR dev $IFACE;
        ip -6 route del ${PREFIX1}/${PREFIX1LEN} via $REMOTE_ADDR dev $IFACE;
    fi

fi

# sample return code. Dibbler will just print it out.
exit 0
