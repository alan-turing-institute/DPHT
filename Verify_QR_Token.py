#!/usr/bin/env python3
# Tool to demonstrate and evaluate Differentially Private Health Tokens (DPHT)
# C Hicks, D Butler 02-07-2020
#
# Dependencies:
#   zbar            http://zbar.sourceforge.net
#   opencv-python3  https://pypi.org/project/opencv-python/
#   OpenSSL         https://pypi.org/project/pyOpenSSL/ (deprecated for crypto)

from pyzbar.pyzbar import decode
import OpenSSL
from OpenSSL import crypto
import cv2
import base64


# QR data class is used to load the QR data payload, extract the token
# details and verify the cryptographic signature.
class QR_data():
    def __init__(self, b64_data):
        readPos = 0
        self.raw_data = base64.b85decode(b64_data)
        user_token_length = int.from_bytes(self.raw_data[:1], 'big')
        readPos += 1
        self.user_token = self.raw_data[readPos:readPos+user_token_length]
        readPos += user_token_length
        self.raw_verify_bytes = self.raw_data[0:readPos]
        token_sign_length = int.from_bytes(self.raw_data[readPos:readPos+2], 'big')
        readPos += 2
        self.token_sign_bytes = self.raw_data[readPos:readPos+token_sign_length]

    # Return the user token bytes
    def get_user_token(self):
        return self.user_token.decode('utf-8')

    # Return the cryptographic signature on the unsigned token bytes
    def get_signature(self):
        return self.token_sign_bytes

    # Verify the signature on the certificate
    def verify_signature(self, cert):
        cert_verify = OpenSSL.crypto.verify(cert, self.token_sign_bytes,
                                                self.raw_verify_bytes, 'sha256')
        if cert_verify is None:
            return True
        else:
            return False


# Load health token from QR code, display details and verify signature.
def main():
    signer_cert_filename = 'OpenSSLKeys/sign_cert.pem'
    qr_code_filename = 'token_qr.png'

    # Load signer public key for verifying user health token
    verify_cert_file = open(signer_cert_filename, "r")
    verify_cert = verify_cert_file.read()
    verify_cert_file.close()
    if verify_cert.startswith('-----BEGIN '):
        pubkey = crypto.load_certificate(crypto.FILETYPE_PEM, verify_cert)
    else:
        pubkey = crypto.load_pkcs12(verify_cert).get_certificate()

    # Read QR code
    print('Scanning {} for QR code health token'.format(qr_code_filename))
    try:
        qr_data_base64 = decode(cv2.imread(qr_code_filename))[0].data
    except TypeError:
        print("Health token not found in {}".format(qr_code_filename))
        exit()

    # Read certificate data from QR code
    qr = QR_data(qr_data_base64)
    print('Health token value: {}'.format(qr.get_user_token()))
    print('\tSignature: {}'.format(base64.encodebytes(qr.get_signature())))

    # Verify signature on token data
    print('\t Valid signature: {}'.format(qr.verify_signature(pubkey)))


if __name__ == '__main__':
    main()
