import pytest

from qasccs.secure_channel.protocol import (
    Envelope,
    ProtocolError,
    decode_envelope,
    encode_envelope,
)


def test_envelope_roundtrip_preserves_payload_and_type():
    env = Envelope.new("echo_request", b"hello world")
    data = encode_envelope(env)
    decoded = decode_envelope(data)

    assert decoded.type == "echo_request"
    assert decoded.payload == b"hello world"
    assert decoded.correlation_id == env.correlation_id
    assert decoded.version == 1


def test_envelope_roundtrip_empty_payload():
    env = Envelope.new("echo_request", b"")
    decoded = decode_envelope(encode_envelope(env))
    assert decoded.payload == b""


def test_envelope_roundtrip_binary_payload():
    payload = bytes(range(256)) * 100
    env = Envelope.new("echo_response", payload)
    decoded = decode_envelope(encode_envelope(env))
    assert decoded.payload == payload


def test_envelope_new_generates_unique_correlation_ids():
    a = Envelope.new("echo_request", b"x")
    b = Envelope.new("echo_request", b"x")
    assert a.correlation_id != b.correlation_id


def test_envelope_new_accepts_explicit_correlation_id():
    env = Envelope.new("echo_response", b"x", correlation_id="abc123")
    assert env.correlation_id == "abc123"


def test_decode_envelope_rejects_non_json():
    with pytest.raises(ProtocolError):
        decode_envelope(b"not json at all")


def test_decode_envelope_rejects_unknown_type():
    with pytest.raises(ProtocolError):
        decode_envelope(b'{"type": "not_a_real_type", "version": 1, "correlation_id": "x", "payload_b64": ""}')


def test_decode_envelope_rejects_missing_fields():
    with pytest.raises(ProtocolError):
        decode_envelope(b'{"version": 1}')
