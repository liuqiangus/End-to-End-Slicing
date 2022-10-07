#!bin/bash

echo "stop core network and servers..."

docker exec -it test-oai-hss /bin/bash -c "killall --signal SIGINT oai_hss"
docker exec -it vir-oai-mme /bin/bash -c "killall --signal SIGINT oai_mme"
docker exec -it test-oai-spgwc /bin/bash -c "killall --signal SIGINT spgwc"
docker exec -it vir-oai-spgwu-1 /bin/bash -c "killall --signal SIGINT oai_spgwu"
docker exec -it vir-oai-spgwu-2 /bin/bash -c "killall --signal SIGINT oai_spgwu"
docker exec -it vir-oai-spgwu-3 /bin/bash -c "killall --signal SIGINT oai_spgwu"

# stop server1
docker exec -it vir-oai-spgwu-1 /bin/bash -c "killall --signal SIGINT python3"
# stop server2
docker exec -it vir-oai-spgwu-2 /bin/bash -c "killall --signal SIGINT python3"
# stop server3
docker exec -it vir-oai-spgwu-3 /bin/bash -c "killall --signal SIGINT python3"

############################# do it again ############################
sleep 5
docker exec -it test-oai-hss /bin/bash -c "killall --signal SIGINT oai_hss"
docker exec -it vir-oai-mme /bin/bash -c "killall --signal SIGINT oai_mme"
docker exec -it test-oai-spgwc /bin/bash -c "killall --signal SIGINT spgwc"
docker exec -it vir-oai-spgwu-1 /bin/bash -c "killall --signal SIGINT oai_spgwu"
docker exec -it vir-oai-spgwu-2 /bin/bash -c "killall --signal SIGINT oai_spgwu"
docker exec -it vir-oai-spgwu-3 /bin/bash -c "killall --signal SIGINT oai_spgwu"

# stop server1
docker exec -it vir-oai-spgwu-1 /bin/bash -c "killall --signal SIGINT python3"
# stop server2
docker exec -it vir-oai-spgwu-2 /bin/bash -c "killall --signal SIGINT python3"
# stop server3
docker exec -it vir-oai-spgwu-3 /bin/bash -c "killall --signal SIGINT python3"


echo "core network and servers stoped!"
