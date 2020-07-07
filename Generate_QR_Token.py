#!/usr/bin/env python3
# Tool to demonstrate and evaluate Differentially Private Health Tokens (DPHT)
# C Hicks, D Butler 02-07-2020
#
# Dependencies:
#   qrcode 6.1  https://pypi.org/project/qrcode/
#   matplotlib  https://pypi.org/project/matplotlib/
#   OpenSSL     https://pypi.org/project/pyOpenSSL/ (deprecated for crypto)
#   numpy       https://pypi.org/project/numpy/

import qrcode
import matplotlib.pyplot as plt
import base64
import OpenSSL
import numpy as np
from OpenSSL import crypto
import math
from math import sqrt, pi, exp


# Health Token data object
class TokenData:

    # Initialise health token data
    def __init__(self, user_token):
        self.user_token = user_token  # user_img_arr = np.asarray(user_img)
        self.cert_bytes = self.getByteArray()

    # Return the token data as a byte array with variable field lengths
    def getByteArray(self):
        user_token_length = len(self.user_token).to_bytes(1, 'big')
        user_token_bytes = bytearray(self.user_token, 'utf-8')

        token_bytes = user_token_length + user_token_bytes

        return token_bytes

    # Signs the certificate data using pkey and then returns the certificate
    # data, plus the signature, as a bytearray
    def getSignedCertificateByteArray(self, pkey):
        cert_sign = OpenSSL.crypto.sign(pkey, self.cert_bytes, "sha256")
        cert_sign_len = len(cert_sign).to_bytes(2, 'big')
        cert_sign_bytes = bytearray(cert_sign)

        return self.cert_bytes + cert_sign_len + cert_sign_bytes

# return the token value based on the test_result input. Test result is 0 or 1.
def output_token(test_result, epsilon, k = 2):

    output_correct = (exp(epsilon) - 1) / (exp(epsilon) + k - 1)

    # Flip biased first coin
    coin0 = np.random.choice([0,1], p = [1 - output_correct, output_correct])
    if coin0 == 1:
        # Let token contain real antibody status
        token = test_result
    else:
        # Flip Second Coin
        token = np.random.choice([0,1], p = [1-1/k,1/k])

    return np.array(token)


def generate_signed_token(test_result, epsilon):
    signer_pkey_filename = 'OpenSSLKeys/sign_key.pem'
    qr_code_filename = 'token_qr.png'

    # Define QR code specification
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=2,
    )

    # Create one user token
    user_token_value = output_token(test_result, epsilon)
    user_token = TokenData(str(user_token_value))

    # Load private key for signing user data
    key_file = open(signer_pkey_filename, "r")
    key = key_file.read()
    key_file.close()
    if key.startswith('-----BEGIN '):
        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key)
    else:
        pkey = crypto.load_pkcs12(key).get_privatekey()

    # Get signed user certificate and build QR code
    signed_user_cert = user_token.getSignedCertificateByteArray(pkey)

    qr.add_data(base64.b85encode(signed_user_cert))

    try:
        qr.make(fit=True)
    except qrcode.exceptions.DataOverflowError:
        print('User data too big for QR code.')
        exit()

    qr_img = qr.make_image(fill_color="black", back_color="white")
    plt.imshow(qr_img, cmap='gray')
    plt.axis('off')
    plt.savefig(qr_code_filename, bbox_inches='tight')
    print('Example user health token QR code output to {}'.format(qr_code_filename))
    print('Done.')

    return

# Simulate issuing nUsers health tokens from a prior distribution priorP.
# The number of risk classes k is derived from len(priorP)
# Returns the real user antibody statuses, the randomised health tokens and
# the absolute error between the two.
def simulate_DPHT(nUsers, epsilon, priorP, k=2, silent=True):

    antibody_status = np.random.choice([0,1], size=(nUsers,), p=priorP)
    token_bits = np.zeros(nUsers)

    tokens = np.zeros(nUsers)

    for user in range(nUsers):
            # create token for each user
        true_status = antibody_status[user]
        token = output_token(true_status, epsilon, k=k)
        tokens[user] = token

    token_bits = tokens.astype(int)

    # E(X) = 2(x - 1/4) where x is the fraction of people who hold X on their health token.
    x = np.count_nonzero(token_bits)/float(token_bits.size)

    min_prob = 1 / (exp(epsilon) + k - 1)
    max_prob = exp(epsilon) * min_prob
    e_x = (x-min_prob)/(max_prob-min_prob)
    real_x = np.count_nonzero(antibody_status)/float(antibody_status.size)
    error = abs(real_x-e_x)

    if not silent:
        print('Actual antibody bits: {}'.format(antibody_status))
        print('Real antibody rate: {}'.format(real_x))
        print('DP antibody bits: {}'.format(token_bits))
        print('E[X] = {}'.format(e_x))
        print('error = {}'.format(error))

    return error


def plot_errors(epsilon, priorP, max_users = 200, nIterations = 50, k=2):

    simulation_data_filename = 'DPHT_simulation.png'

    errors = []

    # Simulate between 1 and max_users, nIterations many times
    print('Simulating between 1 and {} users, {} times per batch'.format(max_users, nIterations))
    print('Running...')

    for nUsers in range(1, max_users):
        nUsers_error = 0
        for iter in range(nIterations):
            nUsers_error_temp = simulate_DPHT(nUsers, epsilon, priorP, k=k)
            nUsers_error += nUsers_error_temp
        nUsers_error /= float(nIterations)
        errors += [nUsers_error]

    fig, ax = plt.subplots()
    ax.plot(errors, label = 'Experimental Error')
    ax.set(xlabel='Number of users E[X] computed over', ylabel = 'Average error',
            ylim=[0,0.5], xlim=[1,max_users], title = f'Average error computing E[X] for the Health Token value, for epsilon = {round(epsilon, 3)}')

    error_constant=((exp(epsilon)+k-1)/(exp(epsilon)-1))*sqrt(2*(k-1)*exp(epsilon)/(pi))/(exp(epsilon)+k-1)
    terrors=[error_constant/sqrt(n) for n in range(1,max_users)]
    ax.plot(terrors, color='red', label = 'Estimated Error')
    ax.legend()
    plt.savefig(simulation_data_filename, bbox_inches='tight')


if __name__ == '__main__':

    # set the value of epsilon and the real test_result value
    epsilon = math.log(3)
    test_result = True

    generate_signed_token(test_result, epsilon)

    # set the prior distributon of antibodies
    priorP = [1./50, 49./50]

    plot_errors(epsilon, priorP, max_users = 200, nIterations = 50, k=5)
