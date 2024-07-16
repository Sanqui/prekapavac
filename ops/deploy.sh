#!/bin/bash
echo "sanqui.net: "
ssh -t sanqui.net "\
    cd /var/www/prekapavac/prekapavac && \
    sudo chown -R sanqui: . && \
    git pull --ff-only && \
    sudo chown -R www-data: . && \
    sudo systemctl restart www_prekapavac \
"
echo "https://prekapavac.sanqui.net/"