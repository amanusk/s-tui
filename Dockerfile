FROM alpine:3 as stress

RUN echo "@testing http://nl.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories && \
    apk add --update build-base libaio-dev libattr libbsd-dev libcap-dev libcap-dev libgcrypt-dev jpeg-dev judy-dev@testing keyutils-dev lksctp-tools-dev libatomic zlib-dev kmod-dev xxhash-dev git && \
    git clone --branch V0.14.00 --depth 1 https://github.com/ColinIanKing/stress-ng.git && \
    cd stress-ng && mkdir install-root && \
    make && make DESTDIR=install-root/ install


####### actual image ########

FROM alpine:3

RUN echo "@testing http://nl.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories && \
    apk add --update libaio libattr libbsd libcap libcap libgcrypt jpeg judy@testing keyutils lksctp-tools libatomic zlib kmod-dev xxhash-dev && \
    apk add --update python3 py3-psutil py3-urwid && \
    apk add --update py3-setuptools # for installing python package

COPY --from=stress stress-ng/install-root/ /

ADD . s-tui
RUN cd s-tui && python3 setup.py install

# We could clean-up things if image was squashed
# RUN apk del py3-setuptools && \
#     rm -rf s-tui /tmp/* /var/tmp/* /var/cache/apk/* /var/cache/distfiles/*

ENTRYPOINT /usr/bin/s-tui
