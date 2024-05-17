#/bin/bash
export DISPLAY=:0

# Wait until Grafana website is accessible
while ! curl -s --head --request GET http://172.16.238.19/ | grep "200 OK" > /dev/null; do
    sleep 1
done

# Once the website is accessible, launch the browser in fullscreen mode
chromium-browser --start-fullscreen http://172.16.238.19/ --display=:0 &