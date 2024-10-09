# dmp-alerts
Simple script solution for sending e-mail alerts to relevant parties when a DMP has been created or updated with relevant information.
Primarily to be used with [cth-dmps API](https://github.com/ChalmersLibrary/cth-dmps-api), but can be adapted for any other environment that can supply searchable DMP metadata in RDA Common maDMP format. 

Known problems:
* If experiencing encoding problems (on Linux?) try running the script as: PYTHONIOENCODING=utf-8 python3 dmp-alerts.py

