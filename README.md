# nodeup-xk-io
site behind nodeup.xk.io


### General flow

* User visits landing page, assigned UID and presented with address
* Selects options and pays
* TX perhaps detected via pynode, otherwise each block is processed and detection occurs then
  * new txs are put in 'unprocessed' (todo add 'timeout' for checking txs)
  * on *detection* of tx a node is created
* Each block event tiggers checking all unprocessed txs (and an external API call is made to determine confirmations `:(`)
* When a tx goes above min confs it is added to node life
  * nodes are checked and if they have 0 minutes after 6+ hours of life they are destroyed (should be plenty of time to confirm)
  * set relay fee required by bitcoind high enough to ensure low-fee txs are not relayed to pynode (and thus require a confirmation to be processed)

