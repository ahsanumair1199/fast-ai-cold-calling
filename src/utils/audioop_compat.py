import numpy as np

'''
The `audioop` module is removed in Python 3.13, so we snag its old C implementation and port what we need using numpy.

WORK IN PROGRESS...

TODO: ratecv and lin2ulaw (they are much more involved...)
'''


# copied from https://raw.githubusercontent.com/python/cpython/3.8/Modules/audioop.c
_st_ulaw2linear16 = np.array([
    -32124, -31100, -30076, -29052, -28028, -27004, -25980,
    -24956, -23932, -22908, -21884, -20860, -19836, -18812,
    -17788, -16764, -15996, -15484, -14972, -14460, -13948,
    -13436, -12924, -12412, -11900, -11388, -10876, -10364,
    -9852, -9340, -8828, -8316, -7932, -7676, -7420,
    -7164, -6908, -6652, -6396, -6140, -5884, -5628,
    -5372, -5116, -4860, -4604, -4348, -4092, -3900,
    -3772, -3644, -3516, -3388, -3260, -3132, -3004,
    -2876, -2748, -2620, -2492, -2364, -2236, -2108,
    -1980, -1884, -1820, -1756, -1692, -1628, -1564,
    -1500, -1436, -1372, -1308, -1244, -1180, -1116,
    -1052, -988, -924, -876, -844, -812, -780,
    -748, -716, -684, -652, -620, -588, -556,
    -524, -492, -460, -428, -396, -372, -356,
    -340, -324, -308, -292, -276, -260, -244,
    -228, -212, -196, -180, -164, -148, -132,
    -120, -112, -104, -96, -88, -80, -72,
    -64, -56, -48, -40, -32, -24, -16,
    -8, 0, 32124, 31100, 30076, 29052, 28028,
    27004, 25980, 24956, 23932, 22908, 21884, 20860,
    19836, 18812, 17788, 16764, 15996, 15484, 14972,
    14460, 13948, 13436, 12924, 12412, 11900, 11388,
    10876, 10364, 9852, 9340, 8828, 8316, 7932,
    7676, 7420, 7164, 6908, 6652, 6396, 6140,
    5884, 5628, 5372, 5116, 4860, 4604, 4348,
    4092, 3900, 3772, 3644, 3516, 3388, 3260,
    3132, 3004, 2876, 2748, 2620, 2492, 2364,
    2236, 2108, 1980, 1884, 1820, 1756, 1692,
    1628, 1564, 1500, 1436, 1372, 1308, 1244,
    1180, 1116, 1052, 988, 924, 876, 844,
    812, 780, 748, 716, 684, 652, 620,
    588, 556, 524, 492, 460, 428, 396,
    372, 356, 340, 324, 308, 292, 276,
    260, 244, 228, 212, 196, 180, 164,
    148, 132, 120, 112, 104, 96, 88,
    80, 72, 64, 56, 48, 40, 32,
    24, 16, 8, 0
])


def ulaw2lin(audio, width):  # assumes LE byte order
    if width != 2:
        raise ValueError('Only supports 16 bit audio (2 bytes per sample).')

    audio_numpy = np.frombuffer(audio, dtype=np.uint8)
    audio_numpy = _st_ulaw2linear16[audio_numpy]
    return audio_numpy.astype(np.int16).tobytes()


if __name__ == '__main__':
    import audioop
    audio = b'~\xff\xff\xfe\xff\xff~~\xff\xff~\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff~~~\xff\xff\xff~\xff\xff\xff\xff~~~\xff\xff\xff\xff~\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff~~~~\xff\xff~~~\xff\xff\xff~\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff~\xff\xff\xff~~~\xff\xff\xff~\xff~\xff\xff\xff\xff~\xff\xff\xff\xff~\xff\xfd\xfd\xff\xff\xff||}{y{xy{}\xfe\xfd\xff\xff\xfc\xfc\xfd\xfc\xfd\xfd\xfd\xfd\xfe\xfe\xfe\xfe\xfe\xfc\xfc\xfb\xfc\xfe\xff~~\xfd\xfb\xfb\xf8\xf8\xfd\xfd\xfd}{{{{~\xfe~}}{'
    t1 = ulaw2lin(audio, 2)
    t2 = audioop.ulaw2lin(audio, 2)
    if t1 == t2:
        print('equal :D')
    else:
        print('not equal :(')
