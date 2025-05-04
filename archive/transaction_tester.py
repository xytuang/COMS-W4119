from transaction import Transaction

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from time import time

if __name__ == '__main__':
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    transaction = Transaction(public_key_bytes, time(), "voted for x")

    print(transaction)

    transaction.sign(private_key)

    print(transaction)

    transaction_bytes = transaction.to_bytes(True)

    res = transaction.verify()

    if (res):
        print("Valid transaction!") #Should print this line
    else:
        print("Invalid transaction!")



    # Invalid case
    invalid_private_key = private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    invalid_transaction = Transaction(public_key_bytes, time(), "voted for x")

    invalid_transaction.sign(invalid_private_key)

    res = invalid_transaction.verify()

    if (res):
        print("Valid transaction!")
    else:
        print("Invalid transaction!") # Should print this line


