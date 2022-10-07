#!bin/bash

echo "close configurations ..."

docker info

# start docker containers
sleep 1
docker stop test-cassandra test-oai-hss vir-oai-mme test-oai-spgwc vir-oai-spgwu-1 vir-oai-spgwu-2 vir-oai-spgwu-3



# configure network & iptables
# sleep 1
# sudo sysctl net.ipv4.conf.all.forwarding=1

# sleep 1
# sudo iptables -P FORWARD ACCEPT

# start ODL controller (background)
# ./distribution-karaf-0.5.3-Boron-SR3/bin/karaf & 

# sleep 10 # wait ODL controller to start

echo "close completed (containers, network, iptables)."
