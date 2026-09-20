FROM alpine:3

RUN apk add --update stress-ng python3 py3-psutil py3-urwid py3-setuptools

ADD . s-tui
RUN cd s-tui && python3 setup.py install

# We could clean-up things if image was squashed
# RUN apk del py3-setuptools && \
#     rm -rf s-tui /tmp/* /var/tmp/* /var/cache/apk/* /var/cache/distfiles/*

ENTRYPOINT /usr/bin/s-tui
