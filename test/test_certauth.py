import os
import shutil

from certauth.certauth import main, CertificateAuthority, FileCache

import tempfile
from OpenSSL import crypto
import datetime
import time

def setup_module():
    global TEST_CA_DIR
    TEST_CA_DIR = tempfile.mkdtemp()

    global TEST_CA_ROOT
    TEST_CA_ROOT = os.path.join(TEST_CA_DIR, 'certauth_test_ca.pem')

def teardown_module():
    shutil.rmtree(TEST_CA_DIR)
    assert not os.path.isdir(TEST_CA_DIR)
    assert not os.path.isfile(TEST_CA_ROOT)

def test_create_root():
    ret = main([TEST_CA_ROOT, '-c', 'Test Root Cert'])
    assert ret == 0

def test_file_create_host_cert():
    ret = main([TEST_CA_ROOT, '-d', TEST_CA_DIR, '-n', 'example.com'])
    assert ret == 0
    certfile = os.path.join(TEST_CA_DIR, 'example.com.pem')
    assert os.path.isfile(certfile)

def test_file_create_wildcard_host_cert_force_overwrite():
    ret = main([TEST_CA_ROOT, '-d', TEST_CA_DIR, '--hostname', 'example.com', '-w', '-f'])
    assert ret == 0
    certfile = os.path.join(TEST_CA_DIR, 'example.com.pem')
    assert os.path.isfile(certfile)

def test_file_wildcard():
    ca = CertificateAuthority(TEST_CA_ROOT, 'Test CA', cert_cache=FileCache(TEST_CA_DIR))
    cert, key = ca.get_wildcard_cert('test.example.proxy')
    filename = os.path.join(TEST_CA_DIR, 'example.proxy.pem')
    assert os.path.isfile(filename)
    os.remove(filename)

def test_file_create_already_exists():
    ret = main([TEST_CA_ROOT, '-d', TEST_CA_DIR, '-n', 'example.com', '-w'])
    assert ret == 1
    certfile = os.path.join(TEST_CA_DIR, 'example.com.pem')
    assert os.path.isfile(certfile)
    # remove now
    os.remove(certfile)

def test_in_mem_cert():
    cert_cache = {}
    ca = CertificateAuthority(TEST_CA_ROOT, 'Test CA', cert_cache=cert_cache)
    cert, key = ca.cert_for_host('test.example.proxy')
    assert 'test.example.proxy' in cert_cache, cert_cache.keys()

    cached_value = cert_cache['test.example.proxy']
    cert2, key2 = ca.cert_for_host('test.example.proxy')
    # assert underlying cache unchanged
    assert cached_value == cert_cache['test.example.proxy']

def test_in_mem_wildcard_cert():
    cert_cache = {}
    ca = CertificateAuthority(TEST_CA_ROOT, 'Test CA', cert_cache=cert_cache)
    cert, key = ca.get_wildcard_cert('test.example.proxy')
    assert 'example.proxy' in cert_cache, cert_cache.keys()

    cached_value = cert_cache['example.proxy']
    cert2, key2 = ca.cert_for_host('example.proxy')
    # assert underlying cache unchanged
    assert cached_value == cert_cache['example.proxy']

def test_create_root_already_exists():
    ret = main([TEST_CA_ROOT])
    # not created, already exists
    assert ret == 1
    # remove now
    os.remove(TEST_CA_ROOT)

def test_create_root_subdir():
    # create a new cert in a subdirectory
    subdir = os.path.join(TEST_CA_DIR, 'subdir')

    ca_file = os.path.join(subdir, 'certauth_test_ca.pem')

    ca = CertificateAuthority(ca_file, 'Test CA',
                              cert_not_before=-60 * 60,
                              cert_not_after=60 * 60 * 24 * 3)

    assert os.path.isdir(subdir)
    assert os.path.isfile(ca_file)

    buff = ca.get_root_PKCS12()
    assert len(buff) > 0

    expected_not_before = datetime.datetime.utcnow() - datetime.timedelta(seconds=60 * 60)
    expected_not_after = datetime.datetime.utcnow() + datetime.timedelta(seconds=60 * 60 * 24 * 3)

    cert = crypto.load_pkcs12(buff).get_certificate()

    actual_not_before = datetime.datetime.strptime(
            cert.get_notBefore().decode('ascii'), '%Y%m%d%H%M%SZ')
    actual_not_after = datetime.datetime.strptime(
            cert.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ')

    time.mktime(expected_not_before.utctimetuple())
    assert abs((time.mktime(actual_not_before.utctimetuple()) - time.mktime(expected_not_before.utctimetuple()))) < 10
    assert abs((time.mktime(actual_not_after.utctimetuple()) - time.mktime(expected_not_after.utctimetuple()))) < 10

