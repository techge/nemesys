"""
Parsing of the JSON-format tshark dissectors.
Interpret fields and data types for comparison to an inference result.
"""

import json
from typing import List, Tuple, Dict, Set, Union
from pprint import pprint
import IPython

from netzob.Model.Vocabulary.Messages.RawMessage import RawMessage, AbstractMessage

from validation.tsharkConnector import TsharkConnector


# noinspection PyDictCreation
class ParsingConstants(object):
    """
    Class to hold constants necessary for the interpretation of the tshark dissectors.
    """

    # see https://www.tcpdump.org/linktypes.html
    LINKTYPES = {
        # 'NULL': 0,
        'ETHERNET': 1,
        # IEEE802_5 = 6
        # PPP = 9
        'RAW_IP': 101
        # IEEE802_11 = 105
    }

    # mapping of field names to general value types.
    TYPELOOKUP = {'delimiter': 'chars',
                  'data.data': 'unknown'}
    """:type: Dict[str, str]"""


# noinspection PyDictCreation
class ParsingConstants226(ParsingConstants):
    """
    Class to hold constants necessary for the interpretation of the tshark dissectors.
    Version for tshark 2.2.6 and compatible.

    TODO Determine up to which exact tshark version this JSON output format is used.
    """

    COMPATIBLE_TO = b'2.2.6'

    # names of field nodes in the json which should be ignored.
    IGNORE_FIELDS = [
        'bootp.option.type_raw', 'bootp.option.value_raw', 'bootp.option.end_raw',

        'dns.qry.name.len_raw', 'dns.count.labels_raw',

        'irc.response_raw', 'irc.request_raw', 'irc.response.num_command_raw', 'irc.ctcp_raw',
        'smtp.command_line_raw', 'smtp.response_raw', 'smb.max_raw',
        'lanman.server_raw', 'dcerpc.cn_ctx_item_raw', 'dcerpc.cn_bind_abstract_syntax_raw', 'dcerpc.cn_bind_trans_raw',
        'nbdgm.first_raw', 'nbdgm.node_type_raw',
        'smb.security_blob_raw', 'gss-api_raw', 'spnego_raw', 'spnego.negTokenInit_element_raw',
        'spnego.mechTypes_raw', 'ntlmssp_raw', 'ntlmssp.version_raw', 'ntlmssp.challenge.target_name_raw',
        'ntlmssp.challenge.target_info_raw'
    ]

    EXCLUDE_SUB_FIELDS = [  # a convenience list for debugging: names of fields that need not give a warning if ignored.
        'dns.flags_tree', 'ntp.flags_tree',
        'bootp.flags_tree', 'bootp.fqdn.flags_tree', 'bootp.secs_tree',
        'smb.flags_tree', 'smb.flags2_tree', 'smb.sm_tree', 'smb.server_cap_tree',
        'nbns.flags_tree', 'nbns.nb_flags_tree',
        'smb.setup.action_tree', 'smb.connect.flags_tree', 'smb.tid_tree', 'smb.connect.support_tree',
        'smb.access_mask_tree', 'smb.transaction.flags_tree', 'browser.server_type_tree', 'smb.dfs.flags_tree',

        'smb.file_attribute_tree', 'smb.search.attribute_tree', 'smb.find_first2.flags_tree', 'smb.create_flags_tree',
        'smb.file_attribute_tree', 'smb.share_access_tree', 'smb.create_options_tree', 'smb.security.flags_tree',
        'smb.fid_tree', 'smb.ipc_state_tree', 'smb.dialect_tree',
        'smb.fs_attr_tree', 'smb.nt.notify.completion_filter_tree',

        'smb2.ioctl.function_tree', 'smb.nt.ioctl.completion_filter_tree', 'smb2.ioctl.function_tree',
        'smb.nt.ioctl.completion_filter_tree', 'smb.lock.type_tree'
    ]

    # names of field nodes in the json which should be descended into.
    INCLUDE_SUBFIELDS = [
        'bootp.option.type_tree',

        'Queries', 'Answers', 'Additional records', 'Authoritative nameservers',

        'irc.request_tree', 'irc.response_tree', 'Command parameters', 'irc',

        'smtp.command_line_tree', 'smtp.response_tree',

        'SMB Header', 'Negotiate Protocol Response (0x72)', 'Session Setup AndX Request (0x73)',
        'Session Setup AndX Response (0x73)', 'Tree Connect AndX Request (0x75)', 'Tree Connect AndX Response (0x75)',
        'Maximal Share Access Rights', 'Guest Maximal Share Access Rights',
        'Trans Request (0x25)', 'Trans Response (0x25)', 'Trans2 Request (0x32)', 'Trans2 Response (0x32)',
        'GET_DFS_REFERRAL Parameters', 'GET_DFS_REFERRAL Data', 'Referrals', 'Referral',
        'Logoff AndX Request (0x74)', 'Logoff AndX Response (0x74)',
        'Tree Disconnect Request (0x71)', 'Tree Disconnect Response (0x71)', 'Negotiate Protocol Request (0x72)',
        'Requested Dialects', 'QUERY_PATH_INFO Parameters', 'QUERY_PATH_INFO Data', 'QUERY_FILE_INFO Parameters',
        'QUERY_FILE_INFO Data', 'FIND_FIRST2 Parameters', 'FIND_FIRST2 Data',
        'NT Create AndX Request (0xa2)', 'NT Create AndX Response (0xa2)',
        'Maximal Access Rights', 'Guest Maximal Access Rights',
        'Read AndX Request (0x2e)', 'Read AndX Response (0x2e)', 'QUERY_FS_INFO Parameters', 'QUERY_FS_INFO Data',
        'Close Request (0x04)', 'Close Response (0x04)', 'NT Cancel Request (0xa4)', 'NT Trans Request (0xa0)',
        'NT NOTIFY Setup', 'NT NOTIFY Parameters',
        'NT Trans Response (0xa0)', 'Trans2 Response (0x32)', 'NT IOCTL Setup', 'NT IOCTL Data', 'Range',
        'Write AndX Request (0x2f)', 'Write AndX Response (0x2f)',
        'Locking AndX Request (0x24)', 'Locking AndX Response (0x24)', 'Echo Request (0x2b)', 'Echo Response (0x2b)',
        'Unlocks', 'Unlock', 'Locks', 'Lock', 'SET_FILE_INFO Parameters', 'SET_FILE_INFO Data'
        # 'dcerpc.cn_ctx_item', 'dcerpc.cn_bind_abstract_syntax', 'dcerpc.cn_bind_trans',
        # 'smb.security_blob_tree', 'gss-api',
        # 'spnego', 'spnego.negTokenInit_element', 'spnego.mechTypes_tree', 'spnego.negHints_element',
        # 'ntlmssp', 'ntlmssp.version', 'ntlmssp.challenge.target_name_tree', 'ntlmssp.challenge.target_info',
        # 'Servers', 'lanman.server_tree'
        ]

    # names of field nodes in the json that have a record structure (list[list[tuples], not list[tuples[str, tuple]]).
    RECORD_STRUCTURE = ['Queries', 'Answers',           # in dns, nbns
                        'Authoritative nameservers',    # in dns
                        'Additional records',           # in nbns
                        'Unlocks', 'Locks']             # in smb

    # mapping of field names to general value types.
    # see also Wireshark dissector reference: https://www.wireshark.org/docs/dfref/
    TYPELOOKUP = {'delimiter': 'chars',
                  'data.data': 'unknown'}
    """:type: Dict[str, str]"""

    # ntp
    TYPELOOKUP['ntp.flags'] = 'flags'  # bit field
    TYPELOOKUP['ntp.stratum'] = 'flags'  # or 'int'  # 1 byte integer: byte
    TYPELOOKUP['ntp.ppoll'] = 'int'
    TYPELOOKUP['ntp.precision'] = 'int'  # signed 1 byte integer: sbyte  -  decimal representation of "float" value, behaves like int
    TYPELOOKUP['ntp.rootdelay'] = 'int'  # 4 byte integer: int  -  decimal representation of "float" value, behaves like int
    TYPELOOKUP['ntp.rootdispersion'] = 'int'
    TYPELOOKUP['ntp.refid'] = 'ipv4'  # 'id'  # some id, effectively often an ipv4 is used
    TYPELOOKUP['ntp.reftime'] = 'timestamp'  #
    TYPELOOKUP['ntp.org'] = 'timestamp'
    TYPELOOKUP['ntp.rec'] = 'timestamp'
    TYPELOOKUP['ntp.xmt'] = 'timestamp'
    TYPELOOKUP['ntp.keyid'] = 'id'
    TYPELOOKUP['ntp.mac'] = 'checksum' # message authentication code crc
    TYPELOOKUP['ntp.priv.auth_seq'] = 'int'  # has value: 97
    TYPELOOKUP['ntp.priv.impl'] = 'int'  # has value: 00
    TYPELOOKUP['ntp.priv.reqcode'] = 'int'  # has value: 00

    # dhcp
    TYPELOOKUP['bootp.type'] = 'flags'  # or enum
    TYPELOOKUP['bootp.hw.type'] = 'flags'  # or enum
    TYPELOOKUP['bootp.hw.len'] = 'int'
    TYPELOOKUP['bootp.hops'] = 'int'
    TYPELOOKUP['bootp.id'] = 'id'
    TYPELOOKUP['bootp.secs'] = 'int'
    TYPELOOKUP['bootp.flags'] = 'flags'
    TYPELOOKUP['bootp.ip.client'] = 'ipv4'
    TYPELOOKUP['bootp.ip.your'] = 'ipv4'
    TYPELOOKUP['bootp.ip.server'] = 'ipv4'
    TYPELOOKUP['bootp.ip.relay'] = 'ipv4'
    TYPELOOKUP['bootp.hw.mac_addr'] = 'macaddr'
    TYPELOOKUP['bootp.hw.addr_padding'] = 'bytes'
    TYPELOOKUP['bootp.server'] = 'chars'
    TYPELOOKUP['bootp.file'] = 'chars'
    TYPELOOKUP['bootp.cookie'] = 'id'  # changed from 'bytes'
    TYPELOOKUP['bootp.option.padding'] = 'pad'
    TYPELOOKUP['bootp.option.type'] = 'enum'  # special prehook since the dissector returns the whole option!
                                              # bootp.option.type_tree is walked from there!
    TYPELOOKUP['bootp.option.length'] = 'int'  # has value: 01
    TYPELOOKUP['bootp.option.dhcp'] = 'enum'  # has value: 03
    TYPELOOKUP['bootp.option.hostname'] = 'chars'  # has value: 4f66666963653131
    TYPELOOKUP['bootp.fqdn.flags'] = 'flags'  # uint; has value: 00
    TYPELOOKUP['bootp.fqdn.rcode1'] = 'enum'  # uint; has value: 00
    TYPELOOKUP['bootp.fqdn.rcode2'] = 'enum'  # uint; has value: 00
    TYPELOOKUP['bootp.fqdn.name'] = 'chars'  # has value: 4f666669636531312e626c7565322e6578
    TYPELOOKUP['bootp.option.vendor_class_id'] = 'chars'  # has value: 4d53465420352e30
    TYPELOOKUP['bootp.option.vendor.value'] = 'bytes'  # has value: 5e00
    TYPELOOKUP['bootp.option.request_list_item'] = 'enum'  # uint; has value: 01
    TYPELOOKUP['bootp.option.broadcast_address'] = 'ipv4'  # has value: ac1203ff
    TYPELOOKUP['bootp.option.dhcp_server_id'] = 'ipv4'  # has value: ac120301
    TYPELOOKUP['bootp.option.ip_address_lease_time'] = 'int'  # uint; has value: 00000e10
    TYPELOOKUP['bootp.option.renewal_time_value'] = 'int'  # uint; has value: 00000696
    TYPELOOKUP['bootp.option.rebinding_time_value'] = 'int'  # uint; has value: 00000bdc
    TYPELOOKUP['bootp.option.subnet_mask'] = 'ipv4'  # has value: ffffff00
    TYPELOOKUP['bootp.option.broadcast_address'] = 'ipv4'  # has value: ac1203ff
    TYPELOOKUP['bootp.option.router'] = 'ipv4'  # has value: ac120301
    TYPELOOKUP['bootp.option.domain_name_server'] = 'ipv4'  # has value: ac120301
    TYPELOOKUP['bootp.option.domain_name'] = 'chars'  # has value: 626c7565332e6578
    TYPELOOKUP['bootp.option.requested_ip_address'] = 'ipv4'  # has value: 0a6e30d8
    TYPELOOKUP['bootp.option.dhcp_max_message_size'] = 'int'  # uint; has value: 04ec
    TYPELOOKUP['bootp.client_id.uuid'] = 'id'  # has value: 00000000000000000000000000000000
    TYPELOOKUP['bootp.option.ntp_server'] = 'ipv4'  # has value: c0a800c8
    # these may be behaving like flags
    TYPELOOKUP['bootp.option.client_system_architecture'] = 'enum'  # has value: 0000
    TYPELOOKUP['bootp.client_network_id_major'] = 'int'  # version number; has value: 02
    TYPELOOKUP['bootp.client_network_id_minor'] = 'int'  # version number; has value: 01
    TYPELOOKUP['bootp.option.dhcp_auto_configuration'] = 'enum'  # has value: 01
    TYPELOOKUP['bootp.option.message'] = 'chars'


    # dns
    TYPELOOKUP['dns.id'] = 'id'  # transaction id/"cookie"
    TYPELOOKUP['dns.flags'] = 'flags'
    TYPELOOKUP['dns.count.queries'] = 'int'
    TYPELOOKUP['dns.count.answers'] = 'int'
    TYPELOOKUP['dns.count.auth_rr'] = 'int'
    TYPELOOKUP['dns.count.add_rr'] = 'int'
    TYPELOOKUP['dns.qry.name'] = 'chars'
    TYPELOOKUP['dns.qry.type'] = 'flags'  # or enum
    TYPELOOKUP['dns.qry.class'] = 'flags'  # or enum
    TYPELOOKUP['dns.resp.name'] = 'chars'  # has value: 0a6c697479616c65616b7300
    TYPELOOKUP['dns.resp.type'] = 'flags'  # or enum  # has value: 0001
    TYPELOOKUP['dns.resp.class'] = 'flags'  # or enum  # has value: 0001
    TYPELOOKUP['dns.resp.ttl'] = 'int'  # has value: 0000003c: unsigned
    TYPELOOKUP['dns.resp.len'] = 'int'  # has value: 0004
    TYPELOOKUP['dns.a'] = 'ipv4'  # has value: 0a10000a
    TYPELOOKUP['dns.ns'] = 'chars'  # has value: 012a00
    TYPELOOKUP['dns.ptr.domain_name'] = 'chars'  # has value: 0369726300
    TYPELOOKUP['dns.rr.udp_payload_size'] = 'int'  # has value: 1000
    TYPELOOKUP['dns.resp.ext_rcode'] = 'int'  # has value: 00
    TYPELOOKUP['dns.resp.edns0_version'] = 'int'  # has value: 00
    TYPELOOKUP['dns.resp.z'] = 'flags'  # has value: 8000

    # irc
    TYPELOOKUP['irc.request.prefix'] = 'chars'
    TYPELOOKUP['irc.request.command'] = 'chars'
    TYPELOOKUP['irc.request.trailer'] = 'chars'
    TYPELOOKUP['irc.response.prefix'] = 'chars'  # has value: 677265676f697265312147726567407365636c61622e63732e756373622e656475
    TYPELOOKUP['irc.response.command'] = 'chars'  # has value: 51554954
    TYPELOOKUP['irc.response.trailer'] = 'chars'  # has value: 50696e672074696d656f75743a20363030207365636f6e6473
    TYPELOOKUP['irc.response.num_command'] = 'chars'  # has value: 333532
    TYPELOOKUP['irc.response.command_parameter'] = 'chars'
    TYPELOOKUP['irc.request.command_parameter'] = 'chars'

    # smtp
    TYPELOOKUP['smtp.req.command'] = 'chars'  # has value: 52435054
    TYPELOOKUP['smtp.req.parameter'] = 'chars'  # has value: 546f3a3c6c75632e726f62657461696c6c65407a696c732e65783e
    TYPELOOKUP['smtp.response.code'] = 'chars'  # has value: 323230
    TYPELOOKUP['smtp.rsp.parameter'] = 'chars'

    # smb
    TYPELOOKUP['smb.server_component'] = 'id'  # has value: ff534d42 = ".SMB"
    TYPELOOKUP['smb.cmd'] = 'int'  # has value: 73
    TYPELOOKUP['smb.nt_status'] = 'int'  # has value: 00000000
    TYPELOOKUP['smb.flags'] = 'flags'  # has value: 18
    TYPELOOKUP['smb.flags2'] = 'flags'  # has value: 07c8
    TYPELOOKUP['smb.pid.high'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.signature'] = 'checksum'  # has value: 4253525350594c20
    TYPELOOKUP['smb.reserved'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.tid'] = 'flags'  # originally was 'id' but behaves like flags  # has value: 0000
    TYPELOOKUP['smb.pid'] = 'flags'  # originally was 'id' but behaves like flags  # has value: fffe
    TYPELOOKUP['smb.uid'] = 'flags'  # originally was 'id' but behaves like flags  # has value: 0000
    TYPELOOKUP['smb.mid'] = 'flags'  # originally was 'id' but behaves like flags  # has value: 4000

    # nbns
    TYPELOOKUP['nbns.id'] = 'int'
    TYPELOOKUP['nbns.flags'] = 'flags'  # has value: 0110
    TYPELOOKUP['nbns.count.queries'] = 'int'  # has value: 0001
    TYPELOOKUP['nbns.count.answers'] = 'int'  # has value: 0000
    TYPELOOKUP['nbns.count.auth_rr'] = 'int'  # has value: 0000
    TYPELOOKUP['nbns.count.add_rr'] = 'int'  # has value: 0000
    TYPELOOKUP['nbns.name'] = 'chars'  # has value: 204648464145424545434f4543454d464645464445434f4546464943414341414100
    TYPELOOKUP['nbns.type'] = 'flags'  # or enum  # has value: 0020
    TYPELOOKUP['nbns.class'] = 'flags'  # or enum  # has value: 0001
    TYPELOOKUP['nbns.ttl'] = 'int'  # has value: 000493e0
    TYPELOOKUP['nbns.data_length'] = 'int'  # has value: 0006
    TYPELOOKUP['nbns.nb_flags'] = 'flags'  # has value: 0000
    TYPELOOKUP['nbns.addr'] = 'ipv4'  # has value: ac140205

    # smb - mostly little endian numbers
    TYPELOOKUP['nbss.type'] = 'id'  # has value: 00
    TYPELOOKUP['nbss.length'] = 'int'  # has value: 000038
    TYPELOOKUP['smb.wct'] = 'int'  # has value: 07
    TYPELOOKUP['smb.andxoffset'] = 'int'  # has value: 3800 - little endian
    TYPELOOKUP['smb.connect.support'] = 'int'  # has value: 0100
    TYPELOOKUP['smb.bcc'] = 'int'  # has value: 0700 (Byte count)
    TYPELOOKUP['smb.service'] = 'enum'  # its coded as 8 bit ASCII 'chars', e.g: 49504300 - http://ubiqx.org/cifs/Book.html p. 311
    TYPELOOKUP['smb.native_fs'] = 'chars'  # has value: 0000
    TYPELOOKUP['smb.tpc'] = 'int'  # has value: 1a00
    TYPELOOKUP['smb.tdc'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.mpc'] = 'int'  # has value: 0800
    TYPELOOKUP['smb.mdc'] = 'int'  # has value: 6810
    TYPELOOKUP['smb.msc'] = 'int'  # has value: 00
    TYPELOOKUP['smb.transaction.flags'] = 'flags'  # has value: 0000
    TYPELOOKUP['smb.timeout'] = 'int'  # has value: 88130000
    TYPELOOKUP['smb.pc'] = 'int'  # has value: 1a00
    TYPELOOKUP['smb.po'] = 'int'  # has value: 5c00
    TYPELOOKUP['smb.dc'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.data_offset'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.sc'] = 'int'  # has value: 00
    TYPELOOKUP['smb.trans_name'] = 'chars'  # has value: 5c0050004900500045005c004c0041004e004d0041004e000000
    TYPELOOKUP['smb.padding'] = 'chars'  # has value: 0000
    TYPELOOKUP['smb.pd'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.data_disp'] = 'int'  # has value: 0000
    TYPELOOKUP['lanman.status'] = 'int'  # has value: 0000
    TYPELOOKUP['lanman.convert'] = 'int'  # has value: 3f0f
    TYPELOOKUP['lanman.entry_count'] = 'int'  # has value: 0b00
    TYPELOOKUP['lanman.available_count'] = 'int'  # has value: 0b00
    TYPELOOKUP['lanman.server.name'] = 'chars'  # has value: 44432d424c5545000000000000000000
    TYPELOOKUP['lanman.server.major'] = 'int'  # has value: 05
    TYPELOOKUP['lanman.server.minor'] = 'int'  # has value: 02
    TYPELOOKUP['browser.server_type'] = 'int'  # has value: 2b108400
    TYPELOOKUP['lanman.server.comment'] = 'chars'  # has value: 00
    TYPELOOKUP['smb.ea.error_offset'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.create.time'] = 'timestamp'  # has value: a34bd360ef84cc01
    TYPELOOKUP['smb.access.time'] = 'timestamp'  # has value: a34bd360ef84cc01
    TYPELOOKUP['smb.last_write.time'] = 'timestamp'  # has value: 2bd5dc60ef84cc01
    TYPELOOKUP['smb.change.time'] = 'timestamp'  # has value: 2bd5dc60ef84cc01
    TYPELOOKUP['smb.file_attribute'] = 'flags'  # has value: 26000000
    TYPELOOKUP['smb.unknown_data'] = 'unknown'  # has value: 00000000
    TYPELOOKUP['smb.max_buf'] = 'int'  # has value: 0411
    TYPELOOKUP['smb.max_mpx_count'] = 'int'  # has value: 3200
    TYPELOOKUP['smb.vc'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.session_key'] = 'bytes'  # has value: 00000000
    TYPELOOKUP['smb.security_blob_len'] = 'int'  # has value: 6b00
    TYPELOOKUP['smb.server_cap'] = 'flags'  # has value: d4000080
    TYPELOOKUP['smb.security_blob'] = 'bytes'
    TYPELOOKUP['smb.native_os'] = 'chars'
    TYPELOOKUP['smb.native_lanman'] = 'chars'
    TYPELOOKUP['smb.primary_domain'] = 'chars'  # has value: 0000
    TYPELOOKUP['smb.trans2.cmd'] = 'id'  # has value: 1000
    TYPELOOKUP['smb.max_referral_level'] = 'int'  # has value: 0300
    TYPELOOKUP['smb.file'] = 'chars'  # has value: 5c0042004c005500450034000000
    TYPELOOKUP['smb.setup.action'] = 'flags'  # has value: 0000
    TYPELOOKUP['smb.file_name_len'] = 'int'  # has value: 3000
    TYPELOOKUP['smb.create_flags'] = 'flags'  # has value: 16000000
    TYPELOOKUP['smb.rfid'] = 'id'  # has value: 00000000
    TYPELOOKUP['smb.access_mask'] = 'flags'  # has value: 89000200
    TYPELOOKUP['smb.alloc_size64'] = 'int'  # has value: 0000000000000000
    TYPELOOKUP['smb.share_access'] = 'flags'  # has value: 07000000
    TYPELOOKUP['smb.create.disposition'] = 'flags'  # has value: 01000000
    TYPELOOKUP['smb.create_options'] = 'flags'  # has value: 40000000
    TYPELOOKUP['smb.impersonation.level'] = 'int'  # has value: 02000000
    TYPELOOKUP['smb.security.flags'] = 'flags'  # has value: 00
    TYPELOOKUP['smb.connect.flags'] = 'flags'  # has value: 0800
    TYPELOOKUP['smb.pwlen'] = 'int'  # has value: 0100
    TYPELOOKUP['smb.password'] = 'bytes'  # has value: 00
    TYPELOOKUP['smb.path'] = 'chars'  # has value: 5c005c005700570057005c0049005000430024000000
    TYPELOOKUP['nbss.continuation_data'] = 'bytes'
    TYPELOOKUP['smb.volume.serial'] = 'bytes'  # has value: eff27040
    TYPELOOKUP['smb.volume.label.len'] = 'int'  # has value: 00000000
    TYPELOOKUP['smb.qpi_loi'] = 'int'  # has value: ec03
    TYPELOOKUP['smb.oplock.level'] = 'int'  # has value: 02
    TYPELOOKUP['smb.fid'] = 'int'  # has value: 07c0
    TYPELOOKUP['smb.create.action'] = 'flags'  # has value: 01000000
    TYPELOOKUP['smb.end_of_file'] = 'bytes'  # has value: 6b00000000000000
    TYPELOOKUP['smb.file_type'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.ipc_state'] = 'flags'  # has value: 0700
    TYPELOOKUP['smb.is_directory'] = 'flags'  # has value: 00
    TYPELOOKUP['smb.volume_guid'] = 'id'  # has value: 00000000000000000000000000000000
    TYPELOOKUP['smb.create.file_id_64b'] = 'id'  # has value: 0000000000000000
    TYPELOOKUP['smb.offset'] = 'int'  # has value: 00000000
    TYPELOOKUP['smb.maxcount_low'] = 'int'  # has value: 6b00
    TYPELOOKUP['smb.mincount'] = 'int'  # has value: 6b00
    TYPELOOKUP['smb.maxcount_high'] = 'int'  # has value: 00000000
    TYPELOOKUP['smb.remaining'] = 'int'  # has value: 6b00
    TYPELOOKUP['smb.offset_high'] = 'int'  # has value: 00000000
    TYPELOOKUP['smb.qfsi_loi'] = 'int'  # has value: 0201
    TYPELOOKUP['smb.dialect.index'] = 'int'  # has value: 0500
    TYPELOOKUP['smb.sm'] = 'id'  # has value: 0f
    TYPELOOKUP['smb.max_vcs'] = 'int'  # has value: 0100
    TYPELOOKUP['smb.max_bufsize'] = 'int'  # has value: 04110000
    TYPELOOKUP['smb.max_raw'] = 'int'  # has value: 00000100
    TYPELOOKUP['smb.system.time'] = 'timestamp'  # has value: eec89f561287cc01
    TYPELOOKUP['smb.server_timezone'] = 'id'  # has value: 88ff
    TYPELOOKUP['smb.challenge_length'] = 'int'  # has value: 00
    TYPELOOKUP['smb.server_guid'] = 'id'  # has value: 535ab176fc509c4697f4f3969e6c3d8d
    TYPELOOKUP['smb.dialect'] = 'chars'  # has value: 024e54204c4d20302e313200
    TYPELOOKUP['smb.search.attribute'] = 'flags'  # has value: 1600
    TYPELOOKUP['smb.search_count'] = 'int'  # has value: 5605
    TYPELOOKUP['smb.find_first2.flags'] = 'flags'  # has value: 0600
    TYPELOOKUP['smb.ff2_loi'] = 'int'  # has value: 0401
    TYPELOOKUP['smb.storage_type'] = 'int'  # has value: 00000000
    TYPELOOKUP['smb.search_pattern'] = 'chars'  # has value: 5c002a000000
    TYPELOOKUP['smb.index_number'] = 'int'  # has value: 64bf000000000500
    TYPELOOKUP['smb.dcm'] = 'flags'  # has value: 0000
    TYPELOOKUP['smb.data_len_low'] = 'int'  # has value: 6b00
    TYPELOOKUP['smb.data_len_high'] = 'int'  # has value: 00000000
    TYPELOOKUP['smb.file_data'] = 'chars' # has value:  b'[.ShellClassInfo]\r\nInfoTip...
    TYPELOOKUP['smb.count_low'] = 'int'  # has value: 4800
    TYPELOOKUP['smb.count_high'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.error_class'] = 'int'  # has value: 00
    TYPELOOKUP['smb.error_code'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.fs_attr'] = 'int'  # has value: ff002700
    TYPELOOKUP['smb.fs_max_name_len'] = 'int'  # has value: ff000000
    TYPELOOKUP['smb.fs_name.len'] = 'int'  # has value: 08000000
    TYPELOOKUP['smb.fs_name'] = 'chars'  # has value: 4e00540046005300
    TYPELOOKUP['smb.extra_byte_parameters'] = 'chars'  # has value: b'W\x00i\x00n\x00d\x00o\x00w\x00s\x00 \x00N\x00T...
    TYPELOOKUP['smb.ansi_pwlen'] = 'int'  # has value: 0100
    TYPELOOKUP['smb.unicode_pwlen'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.ansi_password'] = 'bytes'  # has value: 00
    TYPELOOKUP['smb.account'] = 'chars'  # has value: 0000
    TYPELOOKUP['smb.nt.function'] = 'int'  # has value: 0400
    TYPELOOKUP['smb.nt.notify.completion_filter'] = 'flags'  # has value: 17000000
    TYPELOOKUP['smb.nt.notify.watch_tree'] = 'int'  # has value: 00
    TYPELOOKUP['smb.challenge'] = 'bytes'  # has value: 1340e2b3305971f8
    TYPELOOKUP['smb.server'] = 'chars'  # has value: 440043002d0042004c00550045000000
    TYPELOOKUP['pad'] = 'pad'  # has value: 000000
    TYPELOOKUP['smb2.ioctl.function'] = 'enum'  # has value: a8000900
    TYPELOOKUP['smb.nt.ioctl.isfsctl'] = 'enum'  # has value: 01
    TYPELOOKUP['smb.nt.ioctl.completion_filter'] = 'flags'  # has value: 00
    TYPELOOKUP['smb.echo.count'] = 'int'  # has value: 0100
    TYPELOOKUP['smb.echo.data'] = 'bytes'  # has value: 4a6c4a6d4968436c42737200
    TYPELOOKUP['smb.echo.seq_num'] = 'int'  # has value: 0100
    TYPELOOKUP['smb.lock.type'] = 'flags'  # has value: 12
    TYPELOOKUP['smb.lock.length'] = 'int'
    TYPELOOKUP['smb.lock.offset'] = 'int'
    TYPELOOKUP['smb.locking.oplock.level'] = 'int'  # has value: 01
    TYPELOOKUP['smb.locking.num_unlocks'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.locking.num_locks'] = 'int'  # has value: 0000
    TYPELOOKUP['smb.nt_transaction_setup'] = 'bytes'  # has value: 0200644014000580
    TYPELOOKUP['smb2.ioctl.shadow_copy.num_volumes'] = 'int'  # has value: 00000000
    TYPELOOKUP['smb2.ioctl.shadow_copy.num_labels'] = 'int'  # has value: 00000000
    TYPELOOKUP['smb2.ioctl.shadow_copy.count'] = 'int'  # has value: 02000000
    TYPELOOKUP['smb.unicode_password'] = 'bytes'
    TYPELOOKUP['smb.trans_data'] = 'bytes'
    TYPELOOKUP['smb2.unknown'] = 'bytes'  # has value: 0716

# noinspection PyDictCreation
class ParsingConstants263(ParsingConstants226):
    """
    Compatibility for tshark 2.6.3 to 2.6.5

    TODO Determine starting from which exact tshark version this JSON output format is used.

    "_raw" field node values list
    # h - hex bytes
    # p - position
    # l - length
    # b - bitmask
    # t - type
    see line 262ff: https://github.com/wireshark/wireshark/blob/3a514caaf1e3b36eb284c3a566d489aba6df5392/tools/json2pcap/json2pcap.py
    """
    COMPATIBLE_TO = b'2.6.5'

    pass


class MessageTypeIdentifiers(object):
    # fields or combinations of field that identify a message type for a specific protocol
    FOR_PROTCOL = {
        'bootp' : ['bootp.option.dhcp'],
        'dns'   : ['dns.flags', 'dns.qry.type'],
        'nbns'  : ['nbns.flags'],
        'nbss'  : ['nbss.type', {
            'field': 'smb.cmd',
            'filter': lambda v: v != 'ff',
            'select': lambda w: w
        }, {
            'field': 'smb.flags',
            'filter': lambda v: True,
            'select': lambda w: (int.from_bytes(bytes.fromhex(w), "big") & 128) != 0  # first bit denotes request/response
        }],
        'ntp'   : ['ntp.flags', 'ntp.stratum']
    }

    NAMED_TYPES = {  # assumes hex bytes are lower-case
        'bootp.option.dhcp' : {
            '01': 'Discover',
            '02': 'Offer',
            '03': 'Request',
            '04': 'Decline',
            '05': 'ACK',
            '07': 'Release',
            '08': 'Inform',
        },
        'nbss.type' : {
            '00': 'SMB'
        },
        'dns.flags' : {
            '0100': 'Standard query',
            '8182': 'Response (failure)',
            '8183': 'Response (no such name)',
            '8580': 'Response (success)',
        },
        'dns.qry.type': {
            '0001': 'A',
            '0002': 'NS',
            '0010': 'TXT',
            '001c': 'AAAA',
            '000f': 'MX',
            '000c': 'PTR',
            '0006': 'SOA',
            '0021': 'SRV',
        },
        'smb.cmd': {
            '04': 'Close (0x04)',
            '24': 'Locking AndX Request (0x24)',
            '2b': 'Echo Request (0x2b)',
            '2e': 'Read AndX (0x2e)',
            '2f': 'Write AndX Response (0x2f)',
            'a0': 'NT Trans (0xa0)',
            'a2': 'NT Create AndX (0xa2)',
            'a4': 'NT Cancel (0xa4)',
            '71': 'Tree Disconnect (0x71)',
            '72': 'Negotiate Protocol (0x72)',
            '73': 'Session Setup AndX (0x73)',
            '74': 'Logoff AndX (0x74)',
            '75': 'Tree Connect AndX (0x75)',
        },
        'smb.flags': {  # first bit == 0 denotes request
            True: 'response',
            False: 'request',
        },
        'nbns.flags': {
            '0110': 'Name query',
            '2810': 'Registration',
            '2910': 'Registration (recursion)',
            '3010': 'Release',
            '8500': 'Response',
        },
        'ntp.flags': {
            '13': 'v2 client',
            '19': 'v3 symmetric active',
            '1b': 'v3 client',
            '1c': 'v3 server',
            '23': 'v4 client',
            '24': 'v4 server',
            '25': 'v4 broadcast',
            'd9': 'v3 symmetric active (unsynchronized, MAC)',
            'db': 'v3 client (unsynchronized)',
            'dc': 'v3 server (unsynchronized)',
            'e3': 'v4 client (unsynchronized, MAC)',
            'e4': 'v4 server (unsynchronized)',
            'e5': 'v4 broadcast (unsynchronized)',
        },
        # 'ntp.stratum': {
        #     '00': '',
        #     '03': '',
        #     '04': '',
        #     '05': '',
        #     '06': '',
        # }
    }

    @staticmethod
    def __resolveTypeName(fieldname: str, fieldvalue: str):
        return MessageTypeIdentifiers.NAMED_TYPES[fieldname][fieldvalue] \
            if fieldname in MessageTypeIdentifiers.NAMED_TYPES \
               and fieldvalue in MessageTypeIdentifiers.NAMED_TYPES[fieldname] \
            else "{}={}".format(fieldname, fieldvalue)

    @staticmethod
    def typeOfMessage(message: 'ParsedMessage'):
        if message.protocolname in MessageTypeIdentifiers.FOR_PROTCOL:
            idFields = MessageTypeIdentifiers.FOR_PROTCOL[message.protocolname]
            resolvedTypeName = []
            for ifield in idFields:
                if isinstance(ifield, dict):  # complex type identifiers with filter and selector
                    ifv = message.getValuesByName(ifield['field'])
                    if not ifv:
                        continue  # to next field
                    for idvalue in ifv:
                        if ifield['filter'](idvalue):
                            selectedid = ifield['select'](idvalue)
                            resolvedTypeName.append(
                                MessageTypeIdentifiers.__resolveTypeName(ifield['field'], selectedid))
                else:  # simple identifier
                    selectedid = message.getValuesByName(ifield)
                    for ifv in selectedid:
                        # noinspection PyTypeChecker
                        resolvedTypeName.append(MessageTypeIdentifiers.__resolveTypeName(ifield, ifv))
            if len(resolvedTypeName) > 0:
                return ":".join(resolvedTypeName)

        # message identifier not known (outer if-statement)
        # or filter never matched (if-statement inside dict handling branch)
        raise Exception("No message type identifier known for protocol {}".format(message.protocolname))


class DissectionInvalidError(Exception):
    """
    Base Exception for all errors in dissections from tshark
    """
    pass


class DissectionInsufficient(DissectionInvalidError):
    """
    The dissection worked, but the dissector worked insufficient for the message.
    """
    pass


class DissectionTemporaryFailure(DissectionInvalidError):
    """
    Dissection was invalid this time, but this is only temporary. Typically, a second try should be successful.
    """
    pass


class DissectionIncomplete(DissectionInvalidError):
    """
    The parsing of the dissection was not complete.
    This typically happens if the parser does not know parts of the dissector, which behave non-standard.
    """
    def __init__(self, message, rest=None):
        super().__init__(message)
        self.rest = rest


class ParsedMessage(object):
    """
    Representation of the tshark dissection of a message parsed to be accessible in python.
    pyshark is not sufficient here, since it does not allow access to the original raw data.

    The static methods are not thread-safe! Do only use them in a single thread implementation!
    """

    RK = '_raw'

    __tshark = None  # type: TsharkConnector
    """Cache the last used tsharkConnector for reuse."""


    def __init__(self, message: Union[RawMessage, None], layernumber:int=2, relativeToIP:bool=True,
                 failOnUndissectable:bool=True,
                 linktype:int=ParsingConstants.LINKTYPES['ETHERNET']):
        """
        Construct a new ParsedMessage for ``message``.

        :param message: The raw message to be parsed.
        :param layernumber: Message layer to be considered by the dissection.
            The default is 2, -1 is the upmost layer.
        :param relativeToIP: whether layernumber should be interpreted relative to the IP layer.
        :param failOnUndissectable: If the protocol in layernumber has no known dissector (one field: 'data'), fail.
        """
        # entire Netzob RawMessage
        self.message = message
        self.layernumber = layernumber
        self.relativeToIP = relativeToIP
        self.protocols = None
        self.protocolname = None
        self.protocolbytes = None
        self._fieldsflat = None
        self._dissectfull = None
        self.__failOnUndissectable = failOnUndissectable
        self.__constants = None
        if message:
            if not isinstance(message, RawMessage):
                raise TypeError( "The message need to be of type netzob.Model.Vocabulary.Messages.RawMessage. "
                                 "Type of provided message was {} from {}".format(
                    message.__class__.__name__, message.__class__.__module__) )

            self._parse(linktype)


    @staticmethod
    def _getElementByName(listoftuples: List[Tuple[any, any]], name):
        """
        Search a list of tuples for name as the first element of one or multiple tuples.

        :param listoftuples: list of tuples in format [(key, value), (key, value), (key, value)]
        :param name: The key to search for.
        :return: the value, or list of values if multiple tuples with name as key exist
        """
        foundvalues = list()
        try:
            for k, v in listoftuples:
                if name == k:
                    foundvalues.append(v)
        except ValueError:
            raise ValueError("could not parse as list of tuples: {}".format(listoftuples))
        if len(foundvalues) == 0:
            return False
        if len(foundvalues) == 1:
            return foundvalues[0]
        return foundvalues


    ###  #############################################
    ###  Parsing stuff
    ###  #############################################


    def _parse(self, linktype = ParsingConstants.LINKTYPES['ETHERNET']):
        """
        Dissect write self.message.data to the tshark process and parse the result.
        """
        ParsedMessage._parseMultiple([self.message], target=self, layer=self.layernumber,
                                     relativeToIP=self.relativeToIP, linktype=linktype)
        return None


    @staticmethod
    def parseMultiple(messages: List[RawMessage], layer=-1, relativeToIP=False,
                                         failOnUndissectable=True,
                      linktype=ParsingConstants.LINKTYPES['ETHERNET']) -> Dict[RawMessage, 'ParsedMessage']:
        """
        Bulk create ParsedMessages in one tshark run for better performance.

        :param failOnUndissectable:
        :param messages: A list of messages to be dissected.
        :param layer: Protocol layer to parse, default is -1 for the topmost
        :param relativeToIP: whether the layer is given relative to the IP layer.
        :param linktype: base protocol layer of the PCAP file. One of ParsingConstants.LINKTYPES
        :return: A dict of the input ``messages`` mapped to their ``ParsedMessage`` s
        """
        return ParsedMessage._parseMultiple(messages, layer=layer, relativeToIP=relativeToIP,
                                         failOnUndissectable=failOnUndissectable, linktype=linktype)


    @staticmethod
    def _parseMultiple(messages: List[RawMessage], target = None, layer=-1, relativeToIP=False,
                       failOnUndissectable=True, linktype = ParsingConstants.LINKTYPES['ETHERNET'],
                       maxRecursion: int=3) \
            -> Dict[RawMessage, 'ParsedMessage']:
        """
        Bulk create ParsedMessages in one tshark run for better performance.

        >>> from netzob.all import *
        >>> from validation.messageParser import ParsedMessage
        >>> # pkt = PCAPImporter.readFile("../input/irc_ictf2010-42_deduped-100.pcap", importLayer=1).values()
        >>> pkt = PCAPImporter.readFile("../input/dns_ictf2010_deduped-100.pcap", importLayer=1).values()
        >>> pms = ParsedMessage.parseMultiple(pkt)

        :param messages: List of raw messages to parse
        :param target: The object to call _parseJSON() on for each message,
            Prevalently makes sense for parsing a one-message list (see :func:`_parse()`).
            ``None`` results in creating a new ParsedMessage for each item in ``messages``.
        :type target: ParsedMessage
        :param failOnUndissectable: Flag, whether an exception is to be raised if a packet cannot be fully
            dissected or if just a warning is printed instead.
        :param maxRecursion: The maximum depth of recusive retries. If should be decreased by each recursing call.
            If it reaches 0 the recursion is terminated with an RuntimeError.
        :return: A dict mapping the input messages to the created ParsedMessage-objects.
        """
        if len(messages) == 0:
            return {}

        # another linktype needs a different tshark initialization
        if not ParsedMessage.__tshark:
            ParsedMessage.__tshark = TsharkConnector(linktype)
        elif ParsedMessage.__tshark.linktype != linktype:
            ParsedMessage.__tshark.terminate(2)
            ParsedMessage.__tshark = TsharkConnector(linktype)

        prsdmsgs = {}
        n = 1000  # parse in chunks of 1000s
        for iteration, msgChunk in enumerate([messages[i:i + n] for i in range(0, len(messages), n)]):
            if len(msgChunk) == 1000 or iteration > 0:  # give a bit of a status if long running
                print("Working on chunk {:d} of {:d} messages each".format(iteration, n))
            # else:
            #     print("Working on message", msgChunk[0])

            # retry writing and parsing to tshark on JSON failure
            retryCounter = 3
            tjson = None
            while retryCounter > 0:
                for m in msgChunk:
                    if not isinstance(m, RawMessage):
                        raise TypeError(
                            "The messages need to be of type netzob.Model.Vocabulary.Messages.RawMessage. "
                            "Type of provided message was {} from {}".format(
                                m.__class__.__name__, m.__class__.__module__))
                    ParsedMessage.__tshark.writePacket(m.data)
                if not ParsedMessage.__tshark.isRunning():
                    raise RuntimeError("tshark could not be called.")
                tjson = None
                try:
                    tjson = ParsedMessage.__tshark.readPacket()
                except (ValueError, TimeoutError) as e:
                    print("Need to respawn tshark ({})".format(e))
                    ParsedMessage.__tshark.terminate(2)
                    prsdmsgs.update(ParsedMessage._parseMultiple(msgChunk, target, layer, relativeToIP,
                                                                 failOnUndissectable, linktype))
                    print("Stopped for raised exception:", e)
                    # IPython.embed()

                # Parse JSON:
                try:
                    if tjson is None:
                        print("Empty dissection received.")
                        raise json.JSONDecodeError("Empty dissection received.", "", 0)
                    # iterate each main JSON node alongside the corresponding message from the chunk written to tshark
                    dissectjson = json.loads(tjson, object_pairs_hook = list)
                    for paketjson, m in zip(dissectjson, msgChunk):
                        if target:
                            pm = target  # for one single target
                        else:
                            # Prevent individual tshark call for parsing by creating a
                            #   ParsedMessage with message set to None...
                            pm = ParsedMessage(None, layernumber=layer, relativeToIP=relativeToIP,
                                               failOnUndissectable=failOnUndissectable)
                            # ... and set the message afterwards
                            pm.message = m
                        try:
                            pm._parseJSON(paketjson)
                            prsdmsgs[m] = pm
                        except DissectionTemporaryFailure as e:
                            # Retry tshark, e.g., in case of the "No IP layer" exception
                            print("Need to respawn tshark ({})".format(e))
                            ParsedMessage.__tshark.terminate(2)
                            # Prevent an infinite recursion of ParsedMessage._parseMultiple
                            if maxRecursion > 0:
                                prsdmsgs.update(ParsedMessage._parseMultiple(
                                    msgChunk[msgChunk.index(m):], target, target.layernumber, target.relativeToIP,
                                    maxRecursion=maxRecursion-1))
                            else:
                                raise RuntimeError("ParsedMessage._parseMultiple exceeded its recursion limit.")
                            break   # continue with next chunk. The rest of the current chunk
                                    # was taken care of by the above slice in the recursion parameter
                        except DissectionInsufficient as e:
                            pm._fieldsflat = tuple()
                            print(e, "\nCurrent message: {}\nContinuing with next message.".format(m))
                            continue


                    # parsing worked for this chunk so go on with the next.
                    break  # the while
                except json.JSONDecodeError:
                    retryCounter += 1
                    print("Parsing failed for multiple messages for JSON. Retrying.")
            if retryCounter == 0:
                print("Parsing failed for multiple messages for JSON:\n" + tjson if tjson else "[none]")
                # There is no typical reason known, when this happens, so handle it manually.
                IPython.embed()

        return prsdmsgs  # type: dict[AbstractMessage: ParsedMessage]


    def _parseJSON(self, dissectjson: List[Tuple[str, any]]):
        """
        Read the structure of dissectjson and from this populate:

        * self.protocols
        * self.protocolname
        * self.protocolbytes
        * self._dissectfull
        * self._fieldsflat

        Afterwards do some postprocessing (see :func:`_reassemblePostProcessing()`)

        :param dissectjson: The output of json.loads(), with ``object_pairs_hook = list``
        """
        import subprocess

        sourcekey = '_source'
        layerskey = 'layers'
        framekey = 'frame'
        protocolskey = 'frame.protocols'
        sourcevalue = ParsedMessage._getElementByName(dissectjson, sourcekey)
        if isinstance(sourcevalue, list):
            layersvalue = ParsedMessage._getElementByName(sourcevalue, layerskey)
            if isinstance(layersvalue, list):
                framevalue = ParsedMessage._getElementByName(layersvalue, framekey)
                if isinstance(framevalue, list):
                    protocolsvalue = ParsedMessage._getElementByName(framevalue, protocolskey)
                    if isinstance(protocolsvalue, str):
                        self.protocols = protocolsvalue.split(':')
                        if self.relativeToIP and 'ip' not in self.protocols:
                            errortext = "No IP layer could be identified in a message of the trace."
                            raise DissectionTemporaryFailure(errortext)
                        absLayNum = (self.layernumber if self.layernumber >= 0 else len(self.protocols) - 1) \
                            if not self.relativeToIP else (self.protocols.index('ip') + self.layernumber)
                        try:
                            # protocolname is e.g. 'ntp'
                            self.protocolname = self.protocols[absLayNum]
                        except IndexError as e:
                            ptxt = " ".join([absLayNum, 'missing in', self.protocols])
                            print(ptxt)
                            subprocess.run(["spd-say", ptxt])
                            IPython.embed()
                            raise e
                        self._dissectfull = ParsedMessage._getElementByName(layersvalue, self.protocolname)

                        # add missing layers in protocols list
                        pKeys = [a for a, b in layersvalue]
                        for lnProtocol in self.protocols[absLayNum::-1]:
                            if lnProtocol in pKeys:
                                lastKnownLayer = pKeys.index(lnProtocol)
                                missingLayers = [a for a, b in layersvalue[lastKnownLayer+1:]
                                                if a not in self.protocols # and not a == 'frame'
                                                and not a.endswith(ParsedMessage.RK)]
                                if missingLayers:
                                    print(missingLayers)
                                    self.protocols += missingLayers
                                break

                        # what to do with layers after (embedded in) the target protocol
                        if absLayNum < len(self.protocols):
                            for embedded in self.protocols[absLayNum+1 : ]:
                                dissectsub = ParsedMessage._getElementByName(layersvalue, embedded)
                                if isinstance(dissectsub, list):
                                    self._dissectfull += dissectsub
                                # else:
                                #     print("Bogus protocol layer ignored: {}".format(embedded))

                        # happens for some malformed packets with too few content e.g. irc with only "\r\n" payload
                        if not isinstance(self._dissectfull, list):
                            print ("Undifferentiated protocol content for protocol ", self.protocolname,
                                   "\nDissector JSON is: ", self._dissectfull)
                            subprocess.run(["spd-say", "'Undifferenzierter Protokolinhalt!'"])
                            IPython.embed()  # TODO how to handle this in general without the need for interaction?
                            raise DissectionInsufficient("Undifferentiated protocol content for protocol ", self.protocolname,
                                   "\nDissector JSON is: ", self._dissectfull)
                        if 'tcp.analysis' in [k for k, v in self._dissectfull]:
                            # print("Packet contents for Wireshark filter: {}".format(
                            #     ':'.join([b1 + b2 for b1, b2 in
                            #               zip(self.protocolbytes[::2], self.protocolbytes[1::2])])))
                            raise DissectionTemporaryFailure("Damn tshark expert information.")
                        if 'data.data' in [k for k, v in self._dissectfull]:
                            if self.__failOnUndissectable or \
                                    {k for k, v in self._dissectfull} != {'data.data_raw', 'data.data', 'data.len'}:
                                print(dissectjson)
                                raise DissectionInsufficient(
                                    "Incomplete dissection. Probably wrong base encapsulation detected?")

                        self.protocolbytes = ParsedMessage._getElementByName(layersvalue,
                            self.protocolname + ParsedMessage.RK)  # tshark 2.2.6
                        if isinstance(self.protocolbytes, list):   # tshark 2.6.3
                            self.protocolbytes = self.protocolbytes[0]
                        # field keys, filter for those ending with '_raw' into fieldnames
                        self._fieldsflat = ParsedMessage._walkSubTree(self._dissectfull)
                        try:
                            ParsedMessage._reassemblePostProcessing(self)
                        except DissectionIncomplete as e:
                            print("Known message dissection is", ", ".join(ds[0] for ds in dissectsub))
                            print("Too long unknown message trail found. Rest is:", e.rest,
                                  "\nfor Wireshark filter: {}".format(':'.join([b1 + b2 for b1, b2 in
                                                                                zip(self.protocolbytes[::2],
                                                                                    self.protocolbytes[1::2])])))
                            # it will raise an exception at the following test,
                        except ValueError as e:
                            print(e)

                        # validate dissection
                        if not "".join(self.getFieldValues()) == self.protocolbytes:
                            print("Known message dissection is", ", ".join(ds[0] for ds in dissectsub))
                            print('Dissection is incomplete:\nDissector result:',
                                  '{}\nOriginal  packet: {}\nself is of type ParsedMessage'.format(
                                      "".join(self.getFieldValues()), self.protocolbytes))
                            subprocess.run(["spd-say", "'Dissection unvollständig!'"])
                            IPython.embed()

                            raise DissectionIncomplete('Dissection is incomplete:\nDissector result: {}\n'
                                                       'Original  packet: {}'.format("".join(self.getFieldValues()),
                                                                                     self.protocolbytes))

                        return  # everything worked out

        # if any of the requirements to the structure is not met (see if-conditions above).
        raise DissectionInvalidError('JSON invalid.')


    def _reassemblePostProcessing(self):
        """
        Compare the protocol bytes to the original raw message and insert any bytes
        not accounted for in the fields list as delimiters.

        :raises: ValueError: Delimiters larger than 3 bytes are uncommon and raise an ValueError since most probably a
            field was not parsed correctly. This needs manual postprosessing of the dissector output.
            Therefore see :func:`_prehooks` and :func:`_posthooks`.
        """
        rest = str(self.protocolbytes)
        toInsert = list()
        # iterate all fields and search their value at the next position in the raw message
        for index, raw in enumerate(self.getFieldValues()):
            if not isinstance(raw, str):
                # print("\n_fieldsflat")
                # pprint(self._fieldsflat)
                print("\nThe offending value:")
                pprint(raw)
                raise RuntimeError(
                    "_fieldsflat should only contain strings at the second tuple position, "
                    "something else was there.")

            offset = rest.find(raw)
            if offset > 0:  # remember position and value of delimiters
                if offset > 4:  # a two byte delimiter is probably still reasonable
                    print("Packet:", self.protocolbytes)
                    print("Field sequence:")
                    pprint(self.getFieldSequence())
                    print()


                    # self.printUnknownTypes()
                    # pprint(self._dissectfull)
                    print()
                    raise ValueError("Unparsed field found between field {} and {}. Value: {:s}".format(
                        self.getFieldNames()[index - 1], self.getFieldNames()[index],
                        rest[:offset]) + "\nfor Wireshark filter: {}".format(':'.join([b1 + b2 for b1, b2 in
                                                                                   zip(self.protocolbytes[::2],
                                                                                       self.protocolbytes[1::2])]))
                                     )
                toInsert.append((index, ('delimiter', rest[:offset])))
            nextpos = rest.find(raw) + len(raw)
            rest = rest[nextpos:]
        # insert delimiters into the field list
        for foffset, (index, delim) in enumerate(toInsert):
            self._fieldsflat.insert(index + foffset, delim)
        # if there is any trailing data
        if len(rest) > 0:  # might also be padding (TODO needs evaluation)
            if rest.startswith('20'):  # always consider a space at the start of the rest as delimiter
                self._fieldsflat.append(('delimiter', '20'))
                rest = rest[2:]

            if len(rest) <= 4:  # 2 bytes in hex notation
                self._fieldsflat.append(('delimiter', rest))
            elif self._fieldsflat[-1][0] in ['smb2.ioctl.shadow_copy.count', 'smb.trans_name']:
                # trailer that is unknown to the dissector
                self._fieldsflat.append(('data.data', rest))
            elif set(rest) == {'0'}:  # an all-zero string at the end...
                self._fieldsflat.append(('pad', rest))  # ... is most probably padding if not in dissector
            else:  # a two byte delimiter is probably still reasonable
                raise DissectionIncomplete("Unparsed trailing field found. Value: {:s}".format(rest), rest=rest)


    @staticmethod
    def _nodeValue(node) -> Tuple[int, Union[str, List]]:
        """
        Discern between old and new tshark leaf node format and return value as hex-string
        The return tuple indicates the type of the node:
            * 0: not a leaf node (contains and returns a list not like the tshark 2.6.3 leaf format)
            * 1: old style leaf node (str)
            * 2: new style leaf node (list, but returns the value string)

        :param node:
        :return: Tuple[int, Any]
        """
        # tshark 2.2.6
        if isinstance(node, str):
            return 1, node
        # tshark 2.6.3
        elif isinstance(node, list) and len(node) == 5 \
                and isinstance(node[0], str) \
                and isinstance(node[1], int) and isinstance(node[2], int) \
                and isinstance(node[3], int) and isinstance(node[4], int):
            return 2, node[0]
        else:
            return 0, node


    @staticmethod
    def _walkSubTree(root: List[Tuple[str, any]], allSubFields=False) -> List[Tuple[str, str]]:
        """
        Walk the tree structure of the tshark-json, starting from ``root`` and generate a flat representation
        of the field sequence as it is in the message.

        :param root: A tree structure in "list of (fieldkey, subnode)" tuples.
        :param allSubFields: if True, descend into all sub nodes which are not leaves,
            and append them to the field sequence.

            If False (default), ignore all branch nodes which are not listed in :func:`_includeSubFields`..
        :return:
        """
        CONSTANTS_CLASS = ParsedMessage.__getCompatibleConstants()

        subfields = []
        for fieldkey, subnode in root:
            nodetype, nodevalue = ParsedMessage._nodeValue(subnode)

            # apply pre-hook if any for this field name
            if fieldkey in ParsedMessage._prehooks:
                ranPreHook = ParsedMessage._prehooks[fieldkey](nodevalue, subfields)
                if ranPreHook is not None:
                    subfields.append(ranPreHook)

            # append leaf data
            if fieldkey.endswith(ParsedMessage.RK) and nodetype > 0:
                if fieldkey not in CONSTANTS_CLASS.IGNORE_FIELDS:
                    subfields.append((fieldkey[:-len(ParsedMessage.RK)],
                                      nodevalue))

            # branch node, ignore textual descriptions
            elif nodetype == 0:
                if allSubFields or fieldkey in CONSTANTS_CLASS.INCLUDE_SUBFIELDS:
                    subfields.extend(
                        ParsedMessage._walkSubTree(nodevalue, fieldkey in CONSTANTS_CLASS.RECORD_STRUCTURE))
                elif fieldkey not in CONSTANTS_CLASS.EXCLUDE_SUB_FIELDS:  # to get a notice on errors
                    print("Ignored sub field:", fieldkey)
                    if fieldkey == '_ws.expert':
                        expertMessage = ParsedMessage._getElementByName(nodevalue, '_ws.expert.message')
                        if expertMessage:
                            print(expertMessage)
                        else:
                            print('Malformed packet with unknown error.')

            # apply post-hook, if any, for this field name
            if fieldkey in ParsedMessage._posthooks:
                try:
                    ranPostHook = ParsedMessage._posthooks[fieldkey](nodevalue, subfields)
                except NotImplementedError as e:
                    raise NotImplementedError( "{} Field name: {}".format(e, fieldkey) )
                if ranPostHook is not None:
                    subfields.append(ranPostHook)
        return subfields

        # for structures like irc:
        # ========================
        # "irc": {
        # "irc.response_raw": "3a6972632d7365727665722e6c6f63616c20504f4e47206972632d7365727665722e6c6f63616c203a4c4147323235363235",
        # "irc.response": ":irc-server.local PONG irc-server.local :LAG225625",
        # "irc.response_tree": {    <---
        #   "irc.response.prefix_raw": "6972632d7365727665722e6c6f63616c",
        #   ...
        #   "Command parameters": {
        #     "irc.response.command_parameter_raw": "6972632d7365727665722e6c6f63616c",
        #     "irc.response.command_parameter": "irc-server.local"
        #   },
        #   "irc.response.trailer_raw": "4c4147323235363235",
        #   "irc.response.trailer": "LAG225625"
        # }

        # Record structure:
        # =================
        # "dns": {
        #     "dns.response_to": "1",
        #     ...
        #     "dns.count.add_rr_raw": "0000",
        #     "dns.count.add_rr": "0",
        #     "Queries": {          <---
        #         "a0.twimg.com: type A, class IN": {
        #             "dns.qry.name_raw": "026130057477696d6703636f6d00",
        #             ...



    # TODO move all the hooks into the ParsingConstants class and their mapping
    # TODO enable reuse by providing the original field name to the hook

    # noinspection PyUnusedLocal
    @staticmethod
    def _hookAppendColon(value, siblings: List[Tuple[str, str]]) -> Tuple[str, str]:
        """
        Hook to return a colon as delimiter. See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :return: tuple to add as new field
        """
        return 'delimiter', '3a'


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookAppendSpace(value, siblings) -> Tuple[str, str]:
        """
        Hook to return a space as delimiter. See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        return 'delimiter', '20'


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookAppendColonSpace(value, siblings) -> Tuple[str, str]:
        """
        Hook to return a colon and a space as 2-char delimiter. See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        return 'delimiter', '203a'


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookIRCemptyTrailer(value: str, siblings) -> Tuple[str, str]:
        """
        The silly IRC-dissector outputs no "_raw" value if a field is empty.
        So we need to add the delimiter at least.

        :param value: value of the leaf node we are working on
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        if len(value) == 0:
            return 'delimiter', '203a'


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookAppendCRLF(value, siblings) -> Tuple[str, str]:
        """
        Hook to return a carriage returne and line feed delimiter. See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        return 'delimiter', '0d0a'


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookAppendNetServerEnum2(value, siblings) -> None:
        """
        Hook to fail on LANMAN's Function Code: NetServerEnum2 (104).

        See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        if value == '104':  # Function Code: NetServerEnum2 (104)
            raise NotImplementedError("LANMAN protocol's NetServerEnum2 not supported due to unparsed field at the end "
                                      "of each Server entry in the tshark dissector.")
        return None


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookAppendThreeZeros(value, siblings) -> Tuple[str, str]:
        """
        Hook to return three zero bytes. See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        return 'delimiter', '000000'


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookRaiseNotImpl(value, siblings) -> Tuple[str, str]:
        """
        Hook to fail in case a dissector lacks required field information.

        See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        raise NotImplementedError("Not supported due to unparsed field in the tshark dissector.")


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookAppendFourZeros(value, siblings) -> Tuple[str, str]:
        """
        Hook to return three zero bytes. See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        return 'delimiter', '00000000'


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookAppendUnknownTransParams(value, siblings) -> Tuple[str, str]:
        """
        Hook to return the value of "Unknown Transaction2 Parameters". See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        return 'unknownTrans2params', value


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookAppendUnknownTransData(value, siblings) -> Tuple[str, str]:
        """
        Hook to return the value of "Unknown Transaction2 Parameters". See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        return 'unknownTrans2data', value



    @staticmethod
    def _hookAppendUnknownTransReqBytes(value, siblings) -> Tuple[str, str]:
        """
        Hook to return the value of "Unknown Transaction2 Parameters". See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        if value == '00' and siblings[-1] == ('smb.sc', '03'):
            return 'unknownTransReqBytes', '010001000200'


    # noinspection PyUnusedLocal
    @staticmethod
    def _hookGssapi(value, siblings) -> Tuple[str, str]:
        """
        Hook to return the value of "Unknown Transaction2 Parameters". See :func:`_walkSubTree()`.

        :param value: value of the field we are working on (str or list)
        :param siblings: subfields that we know of by now
        :type siblings: list[tuple[str, str]]
        :return: tuple to add as new field
        """
        return 'gss-api', value[:8]


    @staticmethod
    def _hookFirstByte(value: list, siblings: List[Tuple[str, str]]) -> Tuple[str, str]:
        """
        Hook to return the first byte of the given value for bootp.option.type

        :param value: hex value of the field we are working on
        :param siblings: subfields that we know of by now
        :return: tuple of field name and value to add as new field
        """
        return 'bootp.option.type', value[:2]


    # HOOKS register. See :func:`_walkSubTree()`.
    # noinspection PyUnresolvedReferences
    _prehooks = {
        'bootp.option.type_raw': _hookFirstByte.__func__,

        'irc.response.prefix_raw': _hookAppendColon.__func__,
        'irc.response.trailer_raw': _hookAppendColonSpace.__func__,
        'irc.response.trailer': _hookIRCemptyTrailer.__func__,
        'irc.request.prefix_raw': _hookAppendColon.__func__,
        'irc.request.trailer_raw': _hookAppendColonSpace.__func__,
        'irc.request.trailer': _hookIRCemptyTrailer.__func__,

        'gss-api_raw' : _hookGssapi.__func__,
        'ntlmssp.version.ntlm_current_revision_raw' : _hookAppendThreeZeros.__func__,
    }
    ## Basic handling of missing single delimiter characters is generalized by comparing the original message to the
    ## concatenated dissector result. See :func:`_reassemblePostProcessing()
    ##  within :func:`_reassemblePostProcessing()`
    # noinspection PyUnresolvedReferences
    _posthooks = {
        'lanman.function_code' : _hookAppendNetServerEnum2.__func__,
        'smb.dfs.referral.version' : _hookRaiseNotImpl.__func__,
        'dcerpc.cn_num_ctx_items' : _hookAppendThreeZeros.__func__,
        'Unknown Transaction2 Parameters' : _hookAppendUnknownTransParams.__func__,
        'Unknown Transaction2 Data' : _hookAppendUnknownTransData.__func__,
        'smb.reserved': _hookAppendUnknownTransReqBytes.__func__,
        'nbns.session_data_packet_size' : _hookAppendFourZeros.__func__,
    }


    @staticmethod
    def __getCompatibleConstants():
        """
        Retrieve the ParsingConstants compatible to specific versions of tshark.

        TODO Determine at which exact tshark version the JSON output format is changed.

        :return: Appropriate ParsingConstants class
        """
        if ParsedMessage.__tshark.version <= ParsingConstants226.COMPATIBLE_TO:
            return ParsingConstants226
        elif ParsedMessage.__tshark.version <= ParsingConstants263.COMPATIBLE_TO:
            return ParsingConstants263
        else:
            return ParsingConstants263


    ###  #############################################
    ###  Management stuff
    ###  #############################################

    @staticmethod
    def closetshark():
        if ParsedMessage.__tshark:
            ParsedMessage.__tshark.terminate(2)


    ###  #############################################
    ###  Output handling stuff
    ###  #############################################

    def printUnknownTypes(self):
        """
        Utility method to find which new protocols field types need to be added.
        Prints to the console.

        Example:
        >>> from netzob.all import *
        >>> from validation.messageParser import ParsedMessage
        >>> dns = PCAPImporter.readFile("../input/dns_ictf2010_deduped-100.pcap", importLayer=1).values()
        >>> pms = ParsedMessage.parseMultiple(dns)
        Ignored sub field: dns.id_tree
        Ignored sub field: dns.id_tree
        >>> for parsed in pms.values(): parsed.printUnknownTypes()
        """
        CONSTANTS_CLASS = ParsedMessage.__getCompatibleConstants()
        headerprinted = False
        for fieldname, fieldvalue in self._fieldsflat:
            if not fieldname in CONSTANTS_CLASS.TYPELOOKUP:
                if not headerprinted:  # print if any output before first line
                    print("Known types: " + repr(set(CONSTANTS_CLASS.TYPELOOKUP.values())))
                    headerprinted = True
                print("TYPELOOKUP['{:s}'] = '???'  # has value: {:s}".format(fieldname, fieldvalue))


    def getFieldNames(self) -> List[str]:
        """
        :return: The list of field names of this ParsedMessage.
        """
        return [fk for fk, fv in self._fieldsflat]


    def getFieldValues(self) -> List[str]:
        """
        :return: The list of field values (hexstrings) of this ParsedMessage.
        """
        return [fv for fk, fv in self._fieldsflat]

    def getFieldSequence(self) -> List[Tuple[str, int]]:
        """
        :return: The list of field names and their field lengths of this ParsedMessage.
        """
        return [(fk, len(fv)//2) for fk, fv in self._fieldsflat]

    def getTypeSequence(self) -> Tuple[Tuple[str, int]]:
        """
        :return: The list of field types and their field lengths of this ParsedMessage.
        """
        CONSTANTS_CLASS = ParsedMessage.__getCompatibleConstants()
        retVal = []
        for fk, fv in self._fieldsflat:
            if fk not in CONSTANTS_CLASS.TYPELOOKUP:
                if fk == 'data.data':
                    print(self._dissectfull)
                raise NotImplementedError(
                    "Field name {} has unknown type. hex value: {}".format(fk, fv) +
                    "\nfor Wireshark filter: {}".format(':'.join([b1+b2 for b1, b2 in zip(fv[::2], fv[1::2])])))
            retVal.append((CONSTANTS_CLASS.TYPELOOKUP[fk], len(fv)//2))
        return tuple(retVal)

    def getValuesOfTypes(self) -> Dict[str, Set[str]]:
        """
        :return: A mapping of all field types and their unique values (hexstrings) in this ParsedMessage.
        """
        CONSTANTS_CLASS = ParsedMessage.__getCompatibleConstants()
        retVal = {}
        for fk, fv in self._fieldsflat:
            if fk not in CONSTANTS_CLASS.TYPELOOKUP:
                raise NotImplementedError(
                    "Field name {} has unknown type. The value is {}".format(fk, fv))
            ftype = CONSTANTS_CLASS.TYPELOOKUP[fk]
            if ftype not in retVal:
                retVal[ftype] = set()
            retVal[ftype].add(fv)

        return retVal

    def getValuesByName(self, fieldname):
        """
        Retrieve values of a given field name in this message.

        :param fieldname: The field name to look for in the dissection.
        :return: list of values for all fields with the given fieldname, empty list if non found.
        """
        element = ParsedMessage._getElementByName(self._fieldsflat, fieldname)
        if not element:
            return []
        return element if isinstance(element, list) else [element]

    @property
    def messagetype(self):
        return MessageTypeIdentifiers.typeOfMessage(self)


    def __getstate__(self):
        """
        Include required class arribute in pickling.

        :return: The dict of this object for use in pickle.dump()
        """
        statecopy = self.__dict__.copy()
        statecopy["_ParsedMessage_CLASS___tshark"] = ParsedMessage.__tshark
        return statecopy


    def __setstate__(self, state):
        """
        Include required class arribute in pickling.

        :param state: The dict of this object got from pickle.load()
        """
        # TODO This could be made more efficient by just referencing the class variable once for all instances
        #  by some external wrapper method/class managed by utils.evaluationHelpers.cacheAndLoadDC for pickling
        ParsedMessage.__tshark = state["_ParsedMessage_CLASS___tshark"]
        del state["_ParsedMessage_CLASS___tshark"]
        self.__dict__.update(state)



