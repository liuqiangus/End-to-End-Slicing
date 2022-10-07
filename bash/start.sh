#!bin/bash

echo "start core network and servers ..."

docker exec -d test-oai-hss /bin/bash -c "./bin/oai_hss -j ./etc/hss_rel14.json --reloadkey true"

sleep 1
docker exec -d vir-oai-mme /bin/bash -c "./bin/oai_mme -c ./etc/mme.conf"

sleep 1
docker exec -d test-oai-spgwc /bin/bash -c "cd openair-spgwc; ./build/spgw_c/build/spgwc -o -c etc/spgw_c.conf"

sleep 1
docker exec -d vir-oai-spgwu-1 /bin/bash -c "./bin/oai_spgwu -o -c ./etc/spgw_u.conf"

sleep 1
docker exec -d vir-oai-spgwu-2 /bin/bash -c "./bin/oai_spgwu -o -c ./etc/spgw_u.conf"

sleep 1
docker exec -d vir-oai-spgwu-3 /bin/bash -c "./bin/oai_spgwu -o -c ./etc/spgw_u.conf"


# start server 1
sleep 1
docker exec -d vir-oai-spgwu-1 /bin/bash -c "python3 offloading_servers/asyn_mar_server.py" 

# start server 2
sleep 1
docker exec -d vir-oai-spgwu-2 /bin/bash -c "python3 offloading_servers/asyn_video_server.py"

# start server 3
sleep 1
docker exec -d vir-oai-spgwu-3 /bin/bash -c "python3 offloading_servers/asyn_iot_server.py"


echo "reset docker cpu shares..."
# reset the docker cpu shares to 1
docker update --cpus=1 vir-oai-spgwu-1
docker update --cpus=1 vir-oai-spgwu-2
docker update --cpus=1 vir-oai-spgwu-3
docker update --cpu-shares 1024 vir-oai-spgwu-1
docker update --cpu-shares 1024 vir-oai-spgwu-2
docker update --cpu-shares 1024 vir-oai-spgwu-3
echo "docker cpu shared are reset!"

echo "if there are three pid numbers as follow, then all servers started"
# check if all servers started

echo "oai_hss"
docker exec -it test-oai-hss pidof oai_hss
echo "oai_mme"
docker exec -it vir-oai-mme pidof oai_mme
echo "oai_spgwc"
docker exec -it test-oai-spgwc pidof spgwc
echo "oai_spgwu 1"
docker exec -it vir-oai-spgwu-1 pidof oai_spgwu
echo "oai_spgwu 2"
docker exec -it vir-oai-spgwu-2 pidof oai_spgwu
echo "oai_spgwu 3"
docker exec -it vir-oai-spgwu-3 pidof oai_spgwu
echo "server 1"
docker exec -it vir-oai-spgwu-1 pidof python3
echo "server 2"
docker exec -it vir-oai-spgwu-2 pidof python3
echo "server 3"
docker exec -it vir-oai-spgwu-3 pidof python3


echo "core network and servers started!" 
