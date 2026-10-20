SLOW_START = "slow_start"
CONGESTION_AVOIDANCE = "congestion_avoidance"


class CongestionControl:
    '''
    Maneja la ventana de congestión (cwnd) al estilo TCP Tahoe, solo con
    slow start y congestion avoidance (AIMD).
    Todos los tamaños están en bytes.
    '''

    def __init__(self, MSS: int):
        self.MSS = MSS
        self.cwnd = MSS                     # siempre parte en 1 MSS
        self.ssthresh = None                # se define recién en el primer timeout
        self.current_state = SLOW_START     # siempre parte en slow start

    def get_cwnd(self):
        '''Retorna cwnd en bytes.'''
        return self.cwnd

    def get_MSS_in_cwnd(self):
        '''Retorna cuántos MSS completos caben en cwnd (el 1e-9 evita errores de float).'''
        return int((self.cwnd + 1e-9) // self.MSS)

    def get_ssthresh(self):
        return self.ssthresh

    def is_state_slow_start(self):
        return self.current_state == SLOW_START

    def is_state_congestion_avoidance(self):
        return self.current_state == CONGESTION_AVOIDANCE

    def event_ack_received(self):
        '''Maneja la llegada de un ACK: aumenta cwnd y cambia de estado si corresponde.'''
        if self.is_state_slow_start():
            self.cwnd += self.MSS                       # +1 MSS por ACK
        else:
            self.cwnd += self.MSS / self.get_MSS_in_cwnd()   # +1/MSS_in_cwnd de MSS por ACK

        # si se pasa del umbral, se pasa a congestion avoidance
        if self.is_state_slow_start() and self.ssthresh is not None and self.cwnd >= self.ssthresh:
            self.current_state = CONGESTION_AVOIDANCE

    def event_timeout(self):
        '''Maneja un timeout: ssthresh = cwnd/2, cwnd = 1 MSS y vuelta a slow start.'''
        self.ssthresh = int(self.cwnd / 2)
        self.cwnd = self.MSS
        self.current_state = SLOW_START
