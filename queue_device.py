import zmq

def main(address, fe_port, be_port, be_type = 'connect'):

    try:
        context = zmq.Context(1)
        # Socket facing clients
        frontend = context.socket(zmq.XREP)
        frontend.bind("tcp://%s:%s" % (address, fe_port))
        # Socket facing services
        backend = context.socket(zmq.XREQ)
        #backend.bind("tcp://%s:%s" % (address, be_port))
        if be_type == 'connect':
            backend.connect("tcp://%s:%s" % (address, be_port))
        else:
            backend.bind("tcp://%s:%s" % (address, be_port))

        zmq.device(zmq.QUEUE, frontend, backend)
    except Exception, e:
        print e
        print "bringing down zmq device"
        #raise
    finally:
        pass
        frontend.close()
        backend.close()
        context.term()


if __name__ == "__main__":
    main("127.0.0.1", "5555", "5556")