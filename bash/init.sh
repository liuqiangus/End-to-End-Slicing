#!bin/bash

echo "init configurations ..."

docker info

# start docker containers
sleep 1
docker start test-cassandra test-oai-hss vir-oai-mme test-oai-spgwc vir-oai-spgwu-1 vir-oai-spgwu-2 vir-oai-spgwu-3

# configure network & iptables
sleep 1
sudo sysctl net.ipv4.conf.all.forwarding=1

sleep 1
sudo iptables -P FORWARD ACCEPT

# docker start stream_server
# start the server and streaming
# docker exec -d stream_server /bin/bash -c "while true; do ffmpeg -re -i test.mp4 -c copy -f flv rtmp://127.0.0.1/live/test;done"


# start ODL controller (background)
# ./distribution-karaf-0.5.3-Boron-SR3/bin/karaf & 

# sleep 10 # wait ODL controller to start

echo "init partially completed (containers, network, iptables)."
#echo "You also need run ./distribution-karaf-0.5.3-Boron-SR3/bin/karaf in another terminal"

#read -p 'Did you start karaf? (y/n)' variable

#if [ "$variable" == "y" ]; then
#	echo "you can run: bash start.sh to start core network and servers"
#else
#	echo "!!!!!!!!!!!@@@@@@@@@########## you need run: bash init.sh and karaf !!!!!!!!!!!@@@@@@@@@##########"
#fi
