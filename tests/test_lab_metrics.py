import importlib.util
import pathlib
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / 'filter_plugins' / 'lab_metrics.py'
spec = importlib.util.spec_from_file_location('lab_metrics', MODULE)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


class PingTests(unittest.TestCase):
    def test_linux_success(self):
        text = '5 packets transmitted, 5 received, 0% packet loss, time 4004ms\nrtt min/avg/max/mdev = 0.150/0.220/0.340/0.050 ms'
        actual = metrics.parse_ping(text, 'linux')
        self.assertEqual((actual['sent'], actual['received'], actual['avg_ms']), (5, 5, 0.22))

    def test_routeros_partial_and_mixed_units(self):
        text = 'sent=5 received=4 packet-loss=20% min-rtt=456us avg-rtt=1ms234us max-rtt=2ms'
        actual = metrics.parse_ping(text, 'routeros')
        self.assertEqual((actual['loss_percent'], actual['min_ms'], actual['avg_ms']), (20, 0.456, 1.234))

    def test_total_loss_keeps_rtt_missing(self):
        actual = metrics.parse_ping('sent=5 received=0 packet-loss=100%', 'routeros')
        self.assertEqual(actual['received'], 0)
        self.assertIsNone(actual['avg_ms'])

    def test_missing_or_upper_bound_is_not_zero(self):
        actual = metrics.parse_ping('sent=5 received=5 packet-loss=0% min-rtt=<1ms avg-rtt=<1ms max-rtt=<1ms', 'routeros')
        self.assertIsNone(actual['avg_ms'])
        self.assertTrue(actual['warnings'])
        self.assertIsNone(metrics.parse_ping('unexpected output', 'linux')['sent'])


class ConflictTests(unittest.TestCase):
    desired = {'link_interface': 'ether2', 'loopback_interface': 'lo',
               'link_address': '10.12.0.1/30', 'loopback_address': '10.255.0.1/32',
               'peer_loopback': '10.255.0.2', 'peer_gateway': '10.12.0.2'}
    interfaces = [{'name': name} for name in ('ether1', 'ether2', 'lo')]

    def test_idempotent_existing_addresses_and_route(self):
        addresses = [{'address': '10.12.0.1/30', 'interface': 'ether2'},
                     {'address': '10.255.0.1/32', 'interface': 'lo'}]
        routes = [{'dst-address': '10.255.0.2/32', 'gateway': '10.12.0.2'}]
        result = metrics.plan_router_state(addresses, routes, self.interfaces, self.desired)
        self.assertEqual(result, {'errors': [], 'actions': {'link_address': False, 'loopback_address': False, 'route': False}})

    def test_overlapping_address_and_wrong_route_are_rejected(self):
        addresses = [{'address': '10.12.0.2/30', 'interface': 'ether3'}]
        routes = [{'dst-address': '10.255.0.2/32', 'gateway': '10.12.0.3'}]
        result = metrics.plan_router_state(addresses, routes, self.interfaces, self.desired)
        self.assertEqual(len(result['errors']), 2)


if __name__ == '__main__':
    unittest.main()
