###
# Copyright (2016) Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###
import logging
import unittest
import mock

from copy import deepcopy
from test.utils import ModuleContructorTestCase, PreloadedMocksBaseTestCase
from test.utils import ErrorHandlingTestCase, ValidateEtagTestCase
from hpOneView.exceptions import HPOneViewTaskError
from hpOneView.exceptions import HPOneViewException
from oneview_server_profile import get_logger
from oneview_server_profile import ServerProfileModule
from oneview_server_profile import ServerProfileMerger
from oneview_server_profile import MAKE_COMPLIANT_NOT_SUPPORTED, SERVER_PROFILE_CREATED, REMEDIATED_COMPLIANCE, \
    ALREADY_COMPLIANT, SERVER_PROFILE_DELETED, SERVER_PROFILE_UPDATED, SERVER_ALREADY_UPDATED, \
    ERROR_ALLOCATE_SERVER_HARDWARE, SERVER_PROFILE_ALREADY_ABSENT, KEY_CONNECTIONS, \
    KEY_OS_DEPLOYMENT, KEY_ATTRIBUTES, KEY_SAN, KEY_VOLUMES, KEY_PATHS, KEY_BOOT, KEY_BIOS, KEY_BOOT_MODE, \
    KEY_LOCAL_STORAGE, KEY_SAS_LOGICAL_JBODS, KEY_CONTROLLERS, KEY_LOGICAL_DRIVES, KEY_SAS_LOGICAL_JBOD_URI, \
    KEY_MAC_TYPE, KEY_MAC, KEY_SERIAL_NUMBER_TYPE, KEY_SERIAL_NUMBER, KEY_UUID, KEY_WWPN_TYPE, KEY_LUN, KEY_WWNN, \
    KEY_WWPN, KEY_DRIVE_NUMBER, SERVER_PROFILE_OS_DEPLOYMENT_NOT_FOUND, SERVER_PROFILE_ENCLOSURE_GROUP_NOT_FOUND, \
    SERVER_PROFILE_NETWORK_NOT_FOUND, SERVER_HARDWARE_TYPE_NOT_FOUND, VOLUME_NOT_FOUND, STORAGE_POOL_NOT_FOUND, \
    STORAGE_SYSTEM_NOT_FOUND

SERVER_PROFILE_NAME = "Profile101"
SERVER_PROFILE_URI = "/rest/server-profiles/94B55683-173F-4B36-8FA6-EC250BA2328B"
SHT_URI = "/rest/server-hardware-types/94B55683-173F-4B36-8FA6-EC250BA2328B"
ENCLOSURE_GROUP_URI = "/rest/enclosure-groups/ad5e9e88-b858-4935-ba58-017d60a17c89"
TEMPLATE_URI = '/rest/server-profile-templates/9a156b04-fce8-40b0-b0cd-92ced1311dda'
FAKE_SERVER_HARDWARE = {'uri': '/rest/server-hardware/31393736-3831-4753-567h-30335837524E'}

MESSAGE_COMPLIANT_ERROR = MAKE_COMPLIANT_NOT_SUPPORTED.format(SERVER_PROFILE_NAME)
FAKE_MSG_ERROR = 'Fake message error'

TASK_ERROR = HPOneViewTaskError(msg=FAKE_MSG_ERROR, error_code='AssignProfileToDeviceBayError')

BASIC_PROFILE = dict(
    name=SERVER_PROFILE_NAME,
    serverHardwareTypeUri=SHT_URI,
    enclosureGroupUri=ENCLOSURE_GROUP_URI,
    uri=SERVER_PROFILE_URI
)

BASIC_TEMPLATE = dict(
    name="Server-Template-7000",
    serverHardwareTypeUri=SHT_URI,
    enclosureGroupUri=ENCLOSURE_GROUP_URI,
    uri='/rest/server-profile-templates/9a156b04-fce8-40b0-b0cd-92ced1311dda'
)

PARAMS_FOR_PRESENT = dict(
    config='config.json',
    state='present',
    data=BASIC_PROFILE
)

PARAMS_FOR_COMPLIANT = dict(
    config='config.json',
    state='compliant',
    data=dict(name="Server-Template-7000")
)

PARAMS_FOR_ABSENT = dict(
    config='config.json',
    state='absent',
    data=dict(name="Server-Template-7000")
)

CREATED_BASIC_PROFILE = dict(
    affinity="Bay",
    bios=dict(manageBios=False, overriddenSettings=[]),
    boot=dict(manageBoot=False, order=[]),
    bootMode=dict(manageMode=False, mode=None, pxeBootPolicy=None),
    category="server-profile-templates",
    enclosureGroupUri="/rest/enclosure-groups/ad5e9e88-b858-4935-ba58-017d60a17c89",
    name=SERVER_PROFILE_NAME,
    serialNumber='VCGGU8800W',
    serialNumberType="Virtual",
    serverHardwareTypeUri="/rest/server-hardware-types/94B55683-173F-4B36-8FA6-EC250BA2328B",
    serverHardwareUri='/rest/server-hardware/37333036-3831-76jh-4831-303658389766',
    status="OK",
    type="ServerProfileV5",
    uri="/rest/server-profiles/57d3af2a-b6d2-4446-8645-f38dd808ea490",
    serverProfileTemplateUri='/rest/server-profile-templates/9a156b04-fce8-40b0-b0cd-92ced1311dda',
    templateCompliance='Compliant',
    wwnType="Virtual"
)

AVAILABLE_TARGETS = dict(
    category='available-targets',
    targets=[
        dict(enclosureBay=2, serverHardwareUri=''),
        dict(enclosureBay=3, serverHardwareUri='/rest/server-hardware/31393736-3831-4753-567h-30335837524E'),
        dict(enclosureBay=4, serverHardwareUri='/rest/server-hardware/37333036-3831-6776-gdfd-3037583rewr0'),
        dict(enclosureBay=8, serverHardwareUri='/rest/server-hardware/37333036-3831-4753-4831-303158sdf458'),
    ]
)

BOOT_CONN = dict(priority="NotBootable", chapLevel="none")

CONNECTION_1 = dict(id=1, name="connection-1", mac="E2:4B:0D:30:00:29", boot=BOOT_CONN)
CONNECTION_2 = dict(id=2, name="connection-2", mac="E2:4B:0D:30:00:2A", boot=BOOT_CONN)

CONNECTION_1_WITH_WWPN = dict(name="connection-1", wwpnType="Virtual",
                              wwnn="10:00:3a:43:88:50:00:01", wwpn="10:00:3a:43:88:50:00:00")
CONNECTION_2_WITH_WWPN = dict(name="connection-2", wwpnType="Physical",
                              wwnn="10:00:3a:43:88:50:00:03", wwpn="10:00:3a:43:88:50:00:02")

CONN_1_NO_MAC_BASIC_BOOT = dict(id=1, name="connection-1", boot=dict(priority="NotBootable"))
CONN_2_NO_MAC_BASIC_BOOT = dict(id=2, name="connection-2", boot=dict(priority="NotBootable"))

PATH_1 = dict(isEnabled=True, connectionId=1, storageTargets=["20:00:00:02:AC:00:08:D6"])
PATH_2 = dict(isEnabled=True, connectionId=2, storageTargetType="Auto")

VOLUME_1 = dict(id=1, volumeUri="/rest/volume/id1", lun=123, lunType="Auto", storagePaths=[PATH_1, PATH_2])
VOLUME_2 = dict(id=2, volumeUri="/rest/volume/id2", lun=345, lunType="Auto", storagePaths=[])

SAN_STORAGE = dict(hostOSType="Windows 2012 / WS2012 R2",
                   volumeAttachments=[VOLUME_1, VOLUME_2])

OS_CUSTOM_ATTRIBUTES = [dict(name="hostname", value="newhostname"),
                        dict(name="username", value="administrator")]

OS_DEPLOYMENT_SETTINGS = dict(osDeploymentPlanUri="/rest/os-deployment-plans/81decf85-0dff-4a5e-8a95-52994eeb6493",
                              osVolumeUri="/rest/deployed-targets/a166c84a-4964-4f20-b4ba-ef2f154b8596",
                              osCustomAttributes=OS_CUSTOM_ATTRIBUTES)

SAS_LOGICAL_JBOD_1 = dict(id=1, deviceSlot="Mezz 1", name="jbod-1", driveTechnology="SasHdd", status="OK",
                          sasLogicalJBODUri="/rest/sas-logical-jbods/3128c9e6-e3de-43e7-b196-612707b54967")

SAS_LOGICAL_JBOD_2 = dict(id=2, deviceSlot="Mezz 1", name="jbod-2", driveTechnology="SataHdd", status="Pending")

DRIVES_CONTROLLER_EMBEDDED = [dict(driveNumber=1, name="drive-1", raidLevel="RAID1", bootable=False,
                                   sasLogicalJBODId=None),
                              dict(driveNumber=2, name="drive-2", raidLevel="RAID1", bootable=False,
                                   sasLogicalJBODId=None)]

CONTROLLER_EMBEDDED = dict(deviceSlot="Embedded", mode="RAID", initialize=False, importConfiguration=True,
                           logicalDrives=DRIVES_CONTROLLER_EMBEDDED)

DRIVES_CONTROLLER_MEZZ_1 = [dict(name=None, raidLevel="RAID1", bootable=False, sasLogicalJBODId=1),
                            dict(name=None, raidLevel="RAID1", bootable=False, sasLogicalJBODId=2)]
CONTROLLER_MEZZ_1 = dict(deviceSlot="Mezz 1", mode="RAID", initialize=False, importConfiguration=True,
                         logicalDrives=DRIVES_CONTROLLER_MEZZ_1)

INDEX_EMBED = 0
INDEX_MEZZ = 1


def gather_facts(mock_ov_client, created=False, online_update=True):
    compliance_preview = {
        'automaticUpdates': ['fake change.'],
        'isOnlineUpdate': online_update,
        'manualUpdates': [],
        'type': 'ServerProfileCompliancePreviewV1'
    }

    mock_ov_client.server_profiles.get_compliance_preview.return_value = compliance_preview
    mock_ov_client.server_hardware.get.return_value = {}
    facts = {
        'serial_number': CREATED_BASIC_PROFILE.get('serialNumber'),
        'server_profile': CREATED_BASIC_PROFILE,
        'server_hardware': {},
        'compliance_preview': compliance_preview,
        'created': created
    }

    return facts


class ServerProfileModuleSpec(unittest.TestCase,
                              ModuleContructorTestCase,
                              ValidateEtagTestCase,
                              ErrorHandlingTestCase):
    """
    Test the module constructor
    ModuleContructorTestCase has common tests for class constructor and main function

    ErrorHandlingTestCase has common tests for the module error handling.
    """

    def setUp(self):
        self.configure_mocks(self, ServerProfileModule)
        ErrorHandlingTestCase.configure(self, method_to_fire=self.mock_ov_client.server_profiles.get_by_name)
        self.sleep_patch = mock.patch('time.sleep')
        self.sleep_patch.start()
        self.sleep_patch.return_value = None

    def tearDown(self):
        self.sleep_patch.stop()

    @mock.patch.dict('os.environ', dict(LOGFILE='/path/log.txt'))
    @mock.patch.object(logging, 'getLogger')
    @mock.patch.object(logging, 'basicConfig')
    def test_should_config_logging_when_logfile_env_var_defined(self, mock_logging_config, mock_get_logger):
        fake_logger = mock.Mock()
        mock_get_logger.return_value = fake_logger

        get_logger('/home/dev/oneview-ansible/library/oneview_server_profile.py')

        mock_get_logger.assert_called_once_with('oneview_server_profile.py')
        fake_logger.addHandler.not_been_called()
        mock_logging_config.assert_called_once_with(level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S',
                                                    format='%(asctime)s %(levelname)s %(name)s %(message)s',
                                                    filename='/path/log.txt', filemode='a')

    @mock.patch.dict('os.environ', dict())
    @mock.patch.object(logging, 'getLogger')
    @mock.patch.object(logging, 'basicConfig')
    @mock.patch.object(logging, 'NullHandler')
    def test_should_add_null_handler_when_logfile_env_var_undefined(self, mock_null_handler, mock_logging_config,
                                                                    mock_get_logger):
        fake_logger = mock.Mock()
        mock_get_logger.return_value = fake_logger

        get_logger('/home/dev/oneview-ansible/library/oneview_server_profile.py')

        mock_get_logger.assert_called_once_with('oneview_server_profile.py')
        fake_logger.addHandler.assert_called_once_with(logging.NullHandler())
        mock_logging_config.not_been_called()

    def test_should_fail_when_server_not_associated_with_template(self):
        fake_server = deepcopy(CREATED_BASIC_PROFILE)
        fake_server['templateCompliance'] = 'Unknown'
        fake_server['serverProfileTemplateUri'] = ''

        self.mock_ov_client.server_profiles.get_by_name.return_value = fake_server
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_COMPLIANT)

        ServerProfileModule().run()

        self.mock_ansible_module.fail_json.assert_called_once_with(msg=MESSAGE_COMPLIANT_ERROR)

    def test_should_not_update_when_already_compliant(self):
        fake_server = deepcopy(CREATED_BASIC_PROFILE)
        mock_facts = gather_facts(self.mock_ov_client)

        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_COMPLIANT)
        self.mock_ov_client.server_profiles.get_by_name.return_value = fake_server

        ServerProfileModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False, msg=ALREADY_COMPLIANT, ansible_facts=mock_facts)

    def test_should_update_when_not_compliant(self):
        fake_server = deepcopy(CREATED_BASIC_PROFILE)
        fake_server['templateCompliance'] = 'NonCompliant'
        mock_facts = gather_facts(self.mock_ov_client)

        self.mock_ov_client.server_profiles.get_by_name.return_value = fake_server
        self.mock_ov_client.server_profiles.patch.return_value = CREATED_BASIC_PROFILE
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_COMPLIANT)

        ServerProfileModule().run()

        self.mock_ov_client.server_profiles.patch.assert_called_once_with(
            CREATED_BASIC_PROFILE['uri'], 'replace', '/templateCompliance', 'Compliant')

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True, msg=REMEDIATED_COMPLIANCE, ansible_facts=mock_facts)

    def test_should_power_off_when_is_offline_update(self):
        fake_server = deepcopy(CREATED_BASIC_PROFILE)
        fake_server['templateCompliance'] = 'NonCompliant'

        self.mock_ov_client.server_profiles.get_by_name.return_value = fake_server
        self.mock_ov_client.server_profiles.patch.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}

        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_COMPLIANT)

        # shoud power off server to update
        mock_facts = gather_facts(self.mock_ov_client, online_update=False)

        ServerProfileModule().run()

        self.mock_ov_client.server_profiles.patch.assert_called_once_with(
            CREATED_BASIC_PROFILE['uri'], 'replace', '/templateCompliance', 'Compliant')

        power_set_calls = [
            mock.call(dict(powerState='Off', powerControl='PressAndHold'), fake_server['serverHardwareUri']),
            mock.call(dict(powerState='On', powerControl='MomentaryPress'), fake_server['serverHardwareUri'])]

        self.mock_ov_client.server_hardware.update_power_state.assert_has_calls(power_set_calls)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True, msg=REMEDIATED_COMPLIANCE, ansible_facts=mock_facts)

    def test_should_create_with_automatically_selected_hardware_when_not_exists(self):
        profile_data = deepcopy(BASIC_PROFILE)
        profile_data['serverHardwareUri'] = '/rest/server-hardware/31393736-3831-4753-567h-30335837524E'

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_profiles.get_available_targets.return_value = AVAILABLE_TARGETS
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        mock_facts = gather_facts(self.mock_ov_client, created=True)

        ServerProfileModule().run()

        self.mock_ov_client.server_profiles.create.assert_called_once_with(profile_data)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_CREATED,
            ansible_facts=mock_facts
        )

    def test_should_create_from_template_with_automatically_selected_hardware_when_not_exists(self):
        template = deepcopy(BASIC_TEMPLATE)
        profile_from_template = deepcopy(BASIC_PROFILE)

        param_for_present = deepcopy(PARAMS_FOR_PRESENT)
        param_for_present['data']['server_template'] = 'Server-Template-7000'

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_profiles.get_available_targets.return_value = AVAILABLE_TARGETS
        self.mock_ov_client.server_profile_templates.get_by_name.return_value = template
        self.mock_ov_client.server_profile_templates.get_new_profile.return_value = profile_from_template
        self.mock_ov_client.server_profiles.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = param_for_present
        mock_facts = gather_facts(self.mock_ov_client, created=True)

        ServerProfileModule().run()

        expected_profile_data = deepcopy(BASIC_PROFILE)
        expected_profile_data.update(PARAMS_FOR_PRESENT['data'])
        expected_profile_data['serverHardwareUri'] = '/rest/server-hardware/31393736-3831-4753-567h-30335837524E'
        expected_profile_data['serverProfileTemplateUri'] \
            = '/rest/server-profile-templates/9a156b04-fce8-40b0-b0cd-92ced1311dda'

        self.mock_ov_client.server_profiles.create.assert_called_once_with(expected_profile_data)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_CREATED,
            ansible_facts=mock_facts
        )

    def test_should_create_from_template_uri_with_automatically_selected_hardware_when_not_exists(self):
        template = deepcopy(BASIC_TEMPLATE)
        profile_from_template = deepcopy(BASIC_PROFILE)

        param_for_present = deepcopy(PARAMS_FOR_PRESENT)
        param_for_present['data']['serverProfileTemplateUri'] \
            = '/rest/server-profile-templates/31393736-3831-4753-567h-30335837524E'

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_profiles.get_available_targets.return_value = AVAILABLE_TARGETS
        self.mock_ov_client.server_profile_templates.get.return_value = template
        self.mock_ov_client.server_profile_templates.get_new_profile.return_value = profile_from_template
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = param_for_present
        mock_facts = gather_facts(self.mock_ov_client, created=True)

        ServerProfileModule().run()

        expected_profile_data = deepcopy(BASIC_PROFILE)
        expected_profile_data.update(param_for_present['data'])
        expected_profile_data['serverHardwareUri'] = '/rest/server-hardware/31393736-3831-4753-567h-30335837524E'

        self.mock_ov_client.server_profiles.create.assert_called_once_with(expected_profile_data)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_CREATED,
            ansible_facts=mock_facts
        )

    def test_should_create_with_informed_hardware_when_not_exists(self):
        profile_data = deepcopy(BASIC_PROFILE)
        profile_data['serverHardwareUri'] = '/rest/server-hardware/31393736-3831-4753-567h-30335837524E'

        param_for_present = deepcopy(PARAMS_FOR_PRESENT)
        param_for_present['data']['server_hardware'] = "ServerHardwareName"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.get_by.return_value = [FAKE_SERVER_HARDWARE]
        self.mock_ansible_module.params = param_for_present
        mock_facts = gather_facts(self.mock_ov_client, created=True)

        ServerProfileModule().run()

        self.mock_ov_client.server_profiles.create.assert_called_once_with(profile_data)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_CREATED,
            ansible_facts=mock_facts
        )

    def test_should_create_with_informed_hardware_and_template_when_not_exists(self):
        template = deepcopy(BASIC_TEMPLATE)

        profile_from_template = deepcopy(BASIC_PROFILE)

        param_for_present = deepcopy(PARAMS_FOR_PRESENT)
        param_for_present['data']['server_hardware'] = "ServerHardwareName"
        param_for_present['data']['server_template'] = "TemplateA200"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.get_by.return_value = [FAKE_SERVER_HARDWARE]
        self.mock_ov_client.server_profile_templates.get_by_name.return_value = template
        self.mock_ov_client.server_profile_templates.get_new_profile.return_value = profile_from_template
        self.mock_ansible_module.params = param_for_present
        mock_facts = gather_facts(self.mock_ov_client, created=True)

        ServerProfileModule().run()

        expected_profile_data = deepcopy(BASIC_PROFILE)
        expected_profile_data.update(PARAMS_FOR_PRESENT['data'])
        expected_profile_data['serverHardwareUri'] = '/rest/server-hardware/31393736-3831-4753-567h-30335837524E'
        expected_profile_data['serverProfileTemplateUri'] \
            = '/rest/server-profile-templates/9a156b04-fce8-40b0-b0cd-92ced1311dda'

        self.mock_ov_client.server_profiles.create.assert_called_once_with(expected_profile_data)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_CREATED,
            ansible_facts=mock_facts
        )

    def test_should_try_create_with_informed_hardware_25_times_when_not_exists(self):
        param_for_present = deepcopy(PARAMS_FOR_PRESENT)
        param_for_present['data']['server_hardware'] = "ServerHardwareName"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.side_effect = TASK_ERROR
        self.mock_ov_client.server_hardware.get_by.return_value = [FAKE_SERVER_HARDWARE]
        self.mock_ansible_module.params = param_for_present

        ServerProfileModule().run()

        times_get_targets_called = self.mock_ov_client.server_profiles.get_available_targets.call_count
        self.assertEqual(0, times_get_targets_called)

        times_create_called = self.mock_ov_client.server_profiles.create.call_count
        self.assertEqual(25, times_create_called)

        self.mock_ansible_module.fail_json.assert_called_once_with(
            msg=ERROR_ALLOCATE_SERVER_HARDWARE
        )

    def test_should_try_create_with_informed_hardware_2_times_when_not_exists(self):
        profile_data = deepcopy(BASIC_PROFILE)
        profile_data['serverHardwareUri'] = '/rest/server-hardware/31393736-3831-4753-567h-30335837524E'

        params_for_present = deepcopy(PARAMS_FOR_PRESENT)
        params_for_present['data']['server_hardware'] = "ServerHardwareName"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.side_effect = [TASK_ERROR, CREATED_BASIC_PROFILE]
        self.mock_ov_client.server_hardware.get_by.return_value = [FAKE_SERVER_HARDWARE]
        self.mock_ansible_module.params = params_for_present

        mock_facts = gather_facts(self.mock_ov_client, created=True)

        ServerProfileModule().run()

        times_get_targets_called = self.mock_ov_client.server_profiles.get_available_targets.call_count
        self.assertEqual(0, times_get_targets_called)

        create_calls = [mock.call(profile_data), mock.call(profile_data)]
        self.mock_ov_client.server_profiles.create.assert_has_calls(create_calls)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_CREATED,
            ansible_facts=mock_facts
        )

    def test_should_try_create_with_automatically_selected_hardware_25_times_when_not_exists(self):
        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.side_effect = TASK_ERROR
        self.mock_ov_client.server_profiles.get_available_targets.return_value = AVAILABLE_TARGETS
        self.mock_ov_client.server_hardware.get_by.return_value = [FAKE_SERVER_HARDWARE]
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        ServerProfileModule().run()

        times_get_targets_called = self.mock_ov_client.server_profiles.get_available_targets.call_count
        self.assertEqual(25, times_get_targets_called)

        times_create_called = self.mock_ov_client.server_profiles.create.call_count
        self.assertEqual(25, times_create_called)

        self.mock_ansible_module.fail_json.assert_called_once_with(
            msg=ERROR_ALLOCATE_SERVER_HARDWARE
        )

    def test_should_fail_when_exception_is_not_related_with_server_hardware(self):
        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.side_effect = HPOneViewException(FAKE_MSG_ERROR)
        self.mock_ov_client.server_profiles.get_available_targets.return_value = AVAILABLE_TARGETS
        self.mock_ov_client.server_hardware.get_by.return_value = [FAKE_SERVER_HARDWARE]
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        ServerProfileModule().run()

        times_get_targets_called = self.mock_ov_client.server_profiles.get_available_targets.call_count
        self.assertEqual(1, times_get_targets_called)

        times_create_called = self.mock_ov_client.server_profiles.create.call_count
        self.assertEqual(1, times_create_called)

        self.mock_ansible_module.fail_json.assert_called_once_with(
            msg=FAKE_MSG_ERROR
        )

    def test_fail_when_informed_template_not_exist_for_creation(self):
        params_for_present = deepcopy(PARAMS_FOR_PRESENT)
        params_for_present['data']['server_hardware'] = "ServerHardwareName"
        params_for_present['data']['server_template'] = "TemplateA200"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_hardware.get_by.return_value = [FAKE_SERVER_HARDWARE]
        self.mock_ov_client.server_profile_templates.get_by_name.return_value = None
        self.mock_ansible_module.params = params_for_present

        ServerProfileModule().run()

        self.mock_ansible_module.fail_json.assert_called_once_with(
            msg="Informed Server Profile Template 'TemplateA200' not found")

    def test_fail_when_informed_hardware_not_exist_for_creation(self):
        params_for_present = deepcopy(PARAMS_FOR_PRESENT)
        params_for_present['data']['server_hardware'] = "ServerHardwareName"
        params_for_present['data']['server_template'] = "TemplateA200"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_hardware.get_by.return_value = None
        self.mock_ov_client.server_profile_templates.get_by_name.return_value = BASIC_TEMPLATE
        self.mock_ansible_module.params = params_for_present

        ServerProfileModule().run()

        self.mock_ansible_module.fail_json.assert_called_once_with(
            msg="Informed Server Hardware 'ServerHardwareName' not found")

    def test_should_create_without_hardware_when_there_are_any_available(self):
        available_targets = deepcopy(AVAILABLE_TARGETS)
        available_targets['targets'] = []

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_profiles.create.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_profiles.get_available_targets.return_value = available_targets
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)
        mock_facts = gather_facts(self.mock_ov_client, created=True)

        ServerProfileModule().run()

        self.mock_ov_client.server_profiles.create.assert_called_once_with(deepcopy(BASIC_PROFILE))
        power_set_calls = self.mock_ov_client.server_hardware.update_power_state.call_count
        self.assertEqual(0, power_set_calls)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_CREATED,
            ansible_facts=mock_facts
        )

    def test_should_replace_os_deployment_name_by_uri_on_creation(self):
        uri = '/rest/os-deployment-plans/81decf85-0dff-4a5e-8a95-52994eeb6493'

        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_OS_DEPLOYMENT] = dict(osDeploymentPlanName="Deployment Plan Name")

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.os_deployment_plans.get_by_name.return_value = dict(uri=uri)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0][KEY_OS_DEPLOYMENT], dict(osDeploymentPlanUri=uri))

    def test_should_fail_when_deployment_plan_not_found_on_creation(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_OS_DEPLOYMENT] = dict(osDeploymentPlanName="Deployment Plan Name")

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.os_deployment_plans.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_error = SERVER_PROFILE_OS_DEPLOYMENT_NOT_FOUND + "Deployment Plan Name"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_replace_enclosure_group_name_by_uri_on_creation(self):
        uri = '/rest/enclosure-groups/81decf85-0dff-4a5e-8a95-52994eeb6493'

        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['enclosureGroupName'] = "Enclosure Group Name"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.enclosure_groups.get_by.return_value = [dict(uri=uri)]
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0].get('enclosureGroupUri'), uri)
        self.assertFalse(args[0].get('enclosureGroupName'))

    def test_should_fail_when_enclosure_group_not_found_on_creation(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['enclosureGroupName'] = "Enclosure Group Name"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.enclosure_groups.get_by.return_value = []
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_error = SERVER_PROFILE_ENCLOSURE_GROUP_NOT_FOUND + "Enclosure Group Name"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_replace_connections_name_by_uri_on_creation(self):
        conn_1 = dict(name="connection-1", networkUri='/rest/fc-networks/98')
        conn_2 = dict(name="connection-2", networkName='FC Network')
        conn_3 = dict(name="connection-3", networkName='Ethernet Network')

        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [conn_1, conn_2, conn_3]

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.fc_networks.get_by.side_effect = [[dict(uri='/rest/fc-networks/14')], []]
        self.mock_ov_client.ethernet_networks.get_by.return_value = [dict(uri='/rest/ethernet-networks/18')]
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_connections = [dict(name="connection-1", networkUri='/rest/fc-networks/98'),
                                dict(name="connection-2", networkUri='/rest/fc-networks/14'),
                                dict(name="connection-3", networkUri='/rest/ethernet-networks/18')]

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0].get(KEY_CONNECTIONS), expected_connections)

    def test_should_fail_when_network_not_found_on_creation(self):
        conn = dict(name="connection-1", networkName='FC Network')

        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [conn]

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.fc_networks.get_by.return_value = []
        self.mock_ov_client.ethernet_networks.get_by.return_value = []
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_error = SERVER_PROFILE_NETWORK_NOT_FOUND + "FC Network"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_replace_server_hardware_type_name_by_uri(self):
        sht_uri = "/rest/server-hardware-types/BCAB376E-DA2E-450D-B053-0A9AE7E5114C"
        sht = {"name": "SY 480 Gen9 1", "uri": sht_uri}
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['serverHardwareTypeName'] = "SY 480 Gen9 1"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_hardware_types.get_by.return_value = [sht]

        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0].get('serverHardwareTypeUri'), sht_uri)
        self.assertEqual(args[0].get('serverHardwareTypeName'), None)

    def test_should_fail_when_server_hardware_type_name_not_found(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['serverHardwareTypeName'] = "SY 480 Gen9 1"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_hardware_types.get_by.return_value = []
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        expected_error = SERVER_HARDWARE_TYPE_NOT_FOUND + "SY 480 Gen9 1"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_replace_volume_names_by_uri(self):
        volume1 = {"name": "volume1", "uri": "/rest/storage-volumes/1"}
        volume2 = {"name": "volume2", "uri": "/rest/storage-volumes/2"}
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": [
                {"id": 1, "volumeName": "volume1"},
                {"id": 2, "volumeName": "volume2"}
            ]
        }
        expected_dict = deepcopy(params['data'])
        expected_dict['sanStorage']['volumeAttachments'][0] = {"id": 1, "volumeUri": "/rest/storage-volumes/1"}
        expected_dict['sanStorage']['volumeAttachments'][1] = {"id": 2, "volumeUri": "/rest/storage-volumes/2"}

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.volumes.get_by.side_effect = [[volume1], [volume2]]

        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)

    def test_should_not_replace_when_inform_volume_uri(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": [
                {"id": 1, "volumeUri": "/rest/storage-volumes/1"},
                {"id": 2, "volumeUri": "/rest/storage-volumes/2"}
            ]
        }
        expected_dict = deepcopy(params['data'])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)
        self.mock_ov_client.volumes.get_by.assert_not_called()

    def test_should_not_replace_volume_name_when_volume_attachments_is_none(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": None
        }
        expected_dict = deepcopy(params['data'])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)
        self.mock_ov_client.volumes.get_by.assert_not_called()

    def test_should_not_replace_volume_name_when_san_storage_is_none(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = None
        expected_dict = deepcopy(params['data'])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)
        self.mock_ov_client.volumes.get_by.assert_not_called()

    def test_should_fail_when_volume_name_not_found(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": [
                {"id": 1, "volumeName": "volume1"}
            ]}

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.volumes.get_by.return_value = []
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        expected_error = VOLUME_NOT_FOUND + "volume1"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_replace_storage_pool_names_by_uri(self):
        pool1 = {"name": "pool1", "uri": "/rest/storage-pools/1"}
        pool2 = {"name": "pool2", "uri": "/rest/storage-pools/2"}
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": [
                {"id": 1, "volumeStoragePoolName": "pool1"},
                {"id": 2, "volumeStoragePoolName": "pool2"}
            ]
        }
        expected_dict = deepcopy(params['data'])
        expected_dict['sanStorage']['volumeAttachments'][0] = {"id": 1, "volumeStoragePoolUri": "/rest/storage-pools/1"}
        expected_dict['sanStorage']['volumeAttachments'][1] = {"id": 2, "volumeStoragePoolUri": "/rest/storage-pools/2"}

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.storage_pools.get_by.side_effect = [[pool1], [pool2]]

        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)

    def test_should_not_replace_when_inform_storage_pool_uri(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": [
                {"id": 1, "volumeStoragePoolUri": "/rest/storage-volumes/1"},
                {"id": 2, "volumeStoragePoolUri": "/rest/storage-volumes/2"}
            ]
        }
        expected_dict = deepcopy(params['data'])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)
        self.mock_ov_client.storage_pools.get_by.assert_not_called()

    def test_should_not_replace_storage_pool_name_when_volume_attachments_is_none(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": None
        }
        expected_dict = deepcopy(params['data'])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)
        self.mock_ov_client.storage_pools.get_by.assert_not_called()

    def test_should_not_replace_storage_pool_name_when_san_storage_is_none(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = None
        expected_dict = deepcopy(params['data'])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)
        self.mock_ov_client.storage_pools.get_by.assert_not_called()

    def test_should_fail_when_storage_pool_name_not_found(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": [
                {"id": 1, "volumeStoragePoolName": "pool1"}
            ]
        }

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.storage_pools.get_by.return_value = []
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        expected_error = STORAGE_POOL_NOT_FOUND + "pool1"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_replace_storage_system_names_by_uri(self):
        storage_system1 = {"name": "system1", "uri": "/rest/storage-systems/1"}
        storage_system2 = {"name": "system2", "uri": "/rest/storage-systems/2"}
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": [
                {"id": 1, "volumeStorageSystemName": "system1"},
                {"id": 2, "volumeStorageSystemName": "system2"}
            ]
        }
        expected = deepcopy(params['data'])
        expected['sanStorage']['volumeAttachments'][0] = {"id": 1, "volumeStorageSystemUri": "/rest/storage-systems/1"}
        expected['sanStorage']['volumeAttachments'][1] = {"id": 2, "volumeStorageSystemUri": "/rest/storage-systems/2"}

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.storage_systems.get_by.side_effect = [[storage_system1], [storage_system2]]

        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected)

    def test_should_not_replace_when_inform_storage_system_uri(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": [
                {"id": 1, "volumeStorageSystemUri": "/rest/storage-systems/1"},
                {"id": 2, "volumeStorageSystemUri": "/rest/storage-systems/2"}
            ]
        }
        expected_dict = deepcopy(params['data'])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)
        self.mock_ov_client.storage_systems.get_by.assert_not_called()

    def test_should_not_replace_storage_system_name_when_volume_attachments_is_none(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": None
        }
        expected_dict = deepcopy(params['data'])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)
        self.mock_ov_client.storage_systems.get_by.assert_not_called()

    def test_should_not_replace_storage_system_name_when_san_storage_is_none(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = None
        expected_dict = deepcopy(params['data'])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0], expected_dict)
        self.mock_ov_client.storage_systems.get_by.assert_not_called()

    def test_should_fail_when_storage_system_name_not_found(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['sanStorage'] = {
            "volumeAttachments": [
                {"id": 1, "volumeStorageSystemName": "system1"}
            ]
        }

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.storage_systems.get_by.return_value = []
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        expected_error = STORAGE_SYSTEM_NOT_FOUND + "system1"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_replace_enclosure_name_by_uri(self):
        uri = "/rest/enclosures/09SGH100X6J1"
        enclosure = {"name": "Enclosure-474", "uri": uri}
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['enclosureName'] = "Enclosure-474"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.enclosures.get_by.return_value = [enclosure]

        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0].get('enclosureUri'), uri)
        self.assertEqual(args[0].get('enclosureName'), None)

    def test_should_fail_when_enclosure_name_not_found(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['enclosureName'] = "Enclosure-474"

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.enclosures.get_by.return_value = []
        self.mock_ansible_module.params = params

        ServerProfileModule().run()

        expected_error = SERVER_HARDWARE_TYPE_NOT_FOUND + "Enclosure-474"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_remove_mac_from_connections_before_create_when_mac_is_virtual(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [CONNECTION_1, CONNECTION_2]
        params['data'][KEY_MAC_TYPE] = 'Virtual'

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_connections = [deepcopy(CONNECTION_1), deepcopy(CONNECTION_2)]
        expected_connections[0].pop(KEY_MAC)
        expected_connections[1].pop(KEY_MAC)

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0][KEY_CONNECTIONS], expected_connections)

    def test_should_remove_mac_from_connections_before_create_when_mac_is_physical(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [CONNECTION_1, CONNECTION_2]
        params['data'][KEY_MAC_TYPE] = 'Physical'

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_connections = [deepcopy(CONNECTION_1), deepcopy(CONNECTION_2)]
        expected_connections[0].pop(KEY_MAC)
        expected_connections[1].pop(KEY_MAC)

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0][KEY_CONNECTIONS], expected_connections)

    def test_should_remove_serial_number_before_create_when_serial_number_type_is_virtual(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_SERIAL_NUMBER_TYPE] = 'Virtual'
        params['data'][KEY_UUID] = 'eb0e2fac-bbe5-4ad1-84d3-3e38481c9806'
        params['data'][KEY_SERIAL_NUMBER] = 'VCGNC3V000'

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertTrue(KEY_UUID not in args[0])
        self.assertTrue(KEY_SERIAL_NUMBER not in args[0])

    def test_should_remove_serial_number_before_create_when_serial_number_type_is_physical(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_SERIAL_NUMBER_TYPE] = 'Physical'
        params['data'][KEY_UUID] = 'eb0e2fac-bbe5-4ad1-84d3-3e38481c9806'
        params['data'][KEY_SERIAL_NUMBER] = 'VCGNC3V000'

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertTrue(KEY_UUID not in args[0])
        self.assertTrue(KEY_SERIAL_NUMBER not in args[0])

    def test_should_remove_wwpn_from_conns_before_create_when_wwpn_is_virtual_or_physical(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [CONNECTION_1_WITH_WWPN, CONNECTION_2_WITH_WWPN]
        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_connections = [deepcopy(CONNECTION_1_WITH_WWPN), deepcopy(CONNECTION_2_WITH_WWPN)]
        expected_connections[0].pop(KEY_WWNN)
        expected_connections[0].pop(KEY_WWPN)
        expected_connections[1].pop(KEY_WWNN)
        expected_connections[1].pop(KEY_WWPN)

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0][KEY_CONNECTIONS], expected_connections)

    def test_should_remove_drive_number_from_controller_drives_before_create(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_LOCAL_STORAGE] = dict(controllers=[CONTROLLER_EMBEDDED.copy()])

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_drives = deepcopy(DRIVES_CONTROLLER_EMBEDDED)
        expected_drives[0].pop(KEY_DRIVE_NUMBER)
        expected_drives[1].pop(KEY_DRIVE_NUMBER)

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertEqual(args[0][KEY_LOCAL_STORAGE][KEY_CONTROLLERS][0][KEY_LOGICAL_DRIVES], expected_drives)

    def test_should_remove_lun_from_san_volumes_before_create_when_luntype_is_auto(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_SAN] = SAN_STORAGE

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_volumes = [deepcopy(VOLUME_1), deepcopy(VOLUME_2)]
        expected_volumes[0].pop(KEY_LUN)
        expected_volumes[1].pop(KEY_LUN)

        args, _ = self.mock_ov_client.server_profiles.create.call_args
        self.assertFalse(args[0][KEY_SAN][KEY_VOLUMES][0].get(KEY_LUN))
        self.assertFalse(args[0][KEY_SAN][KEY_VOLUMES][1].get(KEY_LUN))

    def test_should_not_fail_creating_basic_server_profile_when_assignment_types_are_virtual(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_MAC_TYPE] = 'Virtual'
        params['data'][KEY_SERIAL_NUMBER_TYPE] = 'Virtual'
        params['data'][KEY_WWPN_TYPE] = 'Virtual'

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        self.mock_ov_client.server_profiles.create.assert_called_once()

    def test_should_not_fail_creating_basic_server_profile_when_assignment_types_are_physical(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_MAC_TYPE] = 'Physical'
        params['data'][KEY_SERIAL_NUMBER_TYPE] = 'Physical'
        params['data'][KEY_WWPN_TYPE] = 'Physical'

        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        self.mock_ov_client.server_profiles.create.assert_called_once()

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_update_when_data_changed(self, mock_resource_compare):
        profile_data = deepcopy(BASIC_PROFILE)
        mock_resource_compare.return_value = False

        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data
        self.mock_ov_client.server_profiles.update.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        mock_facts = gather_facts(self.mock_ov_client)

        ServerProfileModule().run()

        self.mock_ov_client.server_profiles.update.assert_called_once_with(profile_data, SERVER_PROFILE_URI)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_UPDATED,
            ansible_facts=mock_facts
        )

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_power_off_before_update_when_data_changed(self, mock_resource_compare):
        fake_profile_data = deepcopy(BASIC_PROFILE)
        fake_profile_data['serverHardwareUri'] = SHT_URI

        mock_resource_compare.return_value = False

        self.mock_ov_client.server_profiles.get_by_name.return_value = fake_profile_data
        self.mock_ov_client.server_profiles.update.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        mock_facts = gather_facts(self.mock_ov_client)

        ServerProfileModule().run()

        power_set_calls = [
            mock.call(dict(powerState='Off', powerControl='PressAndHold'), SHT_URI),
            mock.call(dict(powerState='On', powerControl='MomentaryPress'), SHT_URI)]
        self.mock_ov_client.server_hardware.update_power_state.assert_has_calls(power_set_calls)

        self.mock_ov_client.server_profiles.update.assert_called_once_with(fake_profile_data, SERVER_PROFILE_URI)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_UPDATED,
            ansible_facts=mock_facts
        )

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_update_when_data_is_equals(self, mock_resource_compare):
        profile_data = deepcopy(CREATED_BASIC_PROFILE)

        mock_resource_compare.return_value = True
        mock_facts = gather_facts(self.mock_ov_client)
        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        ServerProfileModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            msg=SERVER_ALREADY_UPDATED,
            ansible_facts=mock_facts
        )

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_change_power_state_when_data_is_equals(self, mock_resource_compare):
        profile_data = deepcopy(CREATED_BASIC_PROFILE)

        mock_resource_compare.return_value = True
        gather_facts(self.mock_ov_client)
        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        ServerProfileModule().run()

        self.mock_ov_client.server_hardware.update_power_state.not_been_called()

    @mock.patch('oneview_server_profile.resource_compare')
    def test_fail_when_informed_template_not_exist_for_update(self, mock_resource_compare):
        profile_data = deepcopy(CREATED_BASIC_PROFILE)

        params_for_present = deepcopy(PARAMS_FOR_PRESENT)
        params_for_present['data']['server_hardware'] = "ServerHardwareName"
        params_for_present['data']['server_template'] = "TemplateA200"

        mock_resource_compare.return_value = False

        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data
        self.mock_ov_client.server_hardware.get_by.return_value = [FAKE_SERVER_HARDWARE]
        self.mock_ov_client.server_profile_templates.get_by_name.return_value = None

        self.mock_ansible_module.params = params_for_present

        ServerProfileModule().run()

        self.mock_ansible_module.fail_json.assert_called_once_with(
            msg="Informed Server Profile Template 'TemplateA200' not found")

    @mock.patch('oneview_server_profile.resource_compare')
    def test_fail_when_informed_hardware_not_exist_for_update(self, mock_resource_compare):
        profile_data = deepcopy(CREATED_BASIC_PROFILE)

        params_for_present = deepcopy(PARAMS_FOR_PRESENT)
        params_for_present['data']['server_hardware'] = "ServerHardwareName"
        params_for_present['data']['server_template'] = "TemplateA200"

        mock_resource_compare.return_value = False

        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data
        self.mock_ov_client.server_hardware.get_by.return_value = None
        self.mock_ov_client.server_profile_templates.get_by_name.return_value = BASIC_TEMPLATE

        self.mock_ansible_module.params = params_for_present

        ServerProfileModule().run()

        self.mock_ansible_module.fail_json.assert_called_once_with(
            msg="Informed Server Hardware 'ServerHardwareName' not found")

    @mock.patch('oneview_server_profile.resource_compare')
    @mock.patch.object(ServerProfileMerger, 'merge_data')
    def test_should_call_deep_merge_when_resource_found(self, mock_deep_merge, mock_resource_compare):
        server_profile = deepcopy(BASIC_PROFILE)
        self.mock_ov_client.server_profiles.get_by_name.return_value = server_profile
        self.mock_ov_client.server_profiles.update.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        ServerProfileModule().run()

        mock_deep_merge.assert_called_once_with(server_profile, PARAMS_FOR_PRESENT['data'])

    @mock.patch('oneview_server_profile.resource_compare')
    @mock.patch.object(ServerProfileMerger, 'merge_data')
    def test_should_compare_original_and_merged_resource(self, mock_deep_merge, mock_resource_compare):
        server_profile = deepcopy(BASIC_PROFILE)
        merged_data = dict(name="merged data")
        self.mock_ov_client.server_profiles.get_by_name.return_value = server_profile
        self.mock_ov_client.server_profiles.update.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        mock_deep_merge.return_value = merged_data

        ServerProfileModule().run()

        mock_resource_compare.assert_called_once_with(server_profile, merged_data)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_sort_paths_by_connection_id_for_comparison(self, mock_resource_compare):
        """
        When a resource is retrieved by OneView, the order of the storage paths sometimes differs from the order of the
        storage paths saved. To ensure the comparison will work properly, the paths must be sorted by connectionId.
        """
        profile_data = deepcopy(BASIC_PROFILE)
        profile_data[KEY_SAN] = deepcopy(SAN_STORAGE)
        profile_data[KEY_SAN][KEY_VOLUMES][0][KEY_PATHS][0] = deepcopy(PATH_2)  # connectionId = 2
        profile_data[KEY_SAN][KEY_VOLUMES][0][KEY_PATHS][1] = deepcopy(PATH_1)  # connectionId = 1

        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data
        self.mock_ov_client.server_profiles.update.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        ServerProfileModule().run()

        expected_data = deepcopy(BASIC_PROFILE)
        expected_data[KEY_SAN] = deepcopy(SAN_STORAGE)  # paths are ordered by connectionId
        mock_resource_compare.assert_called_once_with(expected_data, mock.ANY)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_sort_jbods_by_id_for_comparison(self, mock_resource_compare):
        """
        When a resource is retrieved by OneView, the order of the SAS Logical JBODs sometimes differs from the order of
        the SAS Logical JBODs saved. To ensure the comparison will work properly, the SAS Logical JBODs must be sorted
        by id.
        """
        profile_data = deepcopy(BASIC_PROFILE)
        profile_data[KEY_LOCAL_STORAGE] = dict()
        profile_data[KEY_LOCAL_STORAGE][KEY_SAS_LOGICAL_JBODS] = [deepcopy(SAS_LOGICAL_JBOD_2),  # id = 2
                                                                  deepcopy(SAS_LOGICAL_JBOD_1)]  # id = 1

        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data
        self.mock_ov_client.server_profiles.update.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        ServerProfileModule().run()

        expected_data = deepcopy(BASIC_PROFILE)
        expected_data[KEY_LOCAL_STORAGE] = dict()
        expected_data[KEY_LOCAL_STORAGE][KEY_SAS_LOGICAL_JBODS] = [deepcopy(SAS_LOGICAL_JBOD_1),  # id = 1
                                                                   deepcopy(SAS_LOGICAL_JBOD_2)]  # id = 2
        mock_resource_compare.assert_called_once_with(expected_data, mock.ANY)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_sort_controllers_by_device_slot_for_comparison(self, mock_resource_compare):
        """
        When a resource is retrieved by OneView, the order of the Controllers sometimes differs from the order of
        the Controllers saved. To ensure the comparison will work properly, the Controllers must be sorted
        by deviceSlot.
        """
        profile_data = deepcopy(BASIC_PROFILE)
        profile_data[KEY_LOCAL_STORAGE] = dict()
        profile_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS] = [deepcopy(CONTROLLER_MEZZ_1),  # deviceSlot = "Mezz 1"
                                                            deepcopy(CONTROLLER_EMBEDDED)]  # deviceSlot = "Embedded"

        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data
        self.mock_ov_client.server_profiles.update.return_value = CREATED_BASIC_PROFILE
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_PRESENT)

        ServerProfileModule().run()

        expected_data = deepcopy(BASIC_PROFILE)
        expected_data[KEY_LOCAL_STORAGE] = dict()
        expected_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS] = [deepcopy(CONTROLLER_EMBEDDED),  # deviceSlot = "Embedded"
                                                             deepcopy(CONTROLLER_MEZZ_1)]  # deviceSlot = "Mezz 1"
        mock_resource_compare.assert_called_once_with(expected_data, mock.ANY)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_replace_os_deployment_name_by_uri_on_update(self, mock_resource_compare):
        uri = '/rest/os-deployment-plans/81decf85-0dff-4a5e-8a95-52994eeb6493'
        mock_resource_compare.return_value = False

        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_OS_DEPLOYMENT] = dict(osDeploymentPlanName="Deployment Plan Name")

        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ov_client.os_deployment_plans.get_by_name.return_value = dict(uri=uri)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0][KEY_OS_DEPLOYMENT], dict(osDeploymentPlanUri=uri))

    def test_should_fail_when_deployment_plan_not_found_on_update(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_OS_DEPLOYMENT] = dict(osDeploymentPlanName="Deployment Plan Name")

        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ov_client.os_deployment_plans.get_by_name.return_value = None
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_error = SERVER_PROFILE_OS_DEPLOYMENT_NOT_FOUND + "Deployment Plan Name"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_replace_enclosure_group_name_by_uri_on_update(self):
        uri = '/rest/enclosure-groups/81decf85-0dff-4a5e-8a95-52994eeb6493'

        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['enclosureGroupName'] = "Enclosure Group Name"

        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ov_client.enclosure_groups.get_by.return_value = [dict(uri=uri)]
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0].get('enclosureGroupUri'), uri)
        self.assertFalse(args[0].get('enclosureGroupName'))

    def test_should_fail_when_enclosure_group_not_found_on_update(self):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data']['enclosureGroupName'] = "Enclosure Group Name"

        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ov_client.enclosure_groups.get_by.return_value = []
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_error = SERVER_PROFILE_ENCLOSURE_GROUP_NOT_FOUND + "Enclosure Group Name"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    def test_should_replace_connections_name_by_uri_on_update(self):
        conn_1 = dict(name="connection-1", networkUri='/rest/fc-networks/98')
        conn_2 = dict(name="connection-2", networkName='FC Network')
        conn_3 = dict(name="connection-3", networkName='Ethernet Network')

        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [conn_1, conn_2, conn_3]

        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ov_client.fc_networks.get_by.side_effect = [[dict(uri='/rest/fc-networks/14')], []]
        self.mock_ov_client.ethernet_networks.get_by.return_value = [dict(uri='/rest/ethernet-networks/18')]
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_connections = [dict(name="connection-1", networkUri='/rest/fc-networks/98'),
                                dict(name="connection-2", networkUri='/rest/fc-networks/14'),
                                dict(name="connection-3", networkUri='/rest/ethernet-networks/18')]

        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0].get(KEY_CONNECTIONS), expected_connections)

    def test_should_fail_when_network_not_found_on_update(self):
        conn = dict(name="connection-1", networkName='FC Network')

        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [conn]

        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ov_client.fc_networks.get_by.return_value = []
        self.mock_ov_client.ethernet_networks.get_by.return_value = []
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_error = SERVER_PROFILE_NETWORK_NOT_FOUND + "FC Network"
        self.mock_ansible_module.fail_json.assert_called_once_with(msg=expected_error)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_remove_mac_from_connections_before_update_when_mac_is_virtual(self, mock_resource_compare):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [CONNECTION_1, CONNECTION_2]
        params['data'][KEY_MAC_TYPE] = 'Virtual'

        mock_resource_compare.return_value = False
        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_connections = [CONNECTION_1, CONNECTION_2]
        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0][KEY_CONNECTIONS], expected_connections)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_remove_mac_from_connections_before_update_when_mac_is_physical(self, mock_resource_compare):
        mock_resource_compare.return_value = False

        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [CONNECTION_1, CONNECTION_2]
        params['data'][KEY_MAC_TYPE] = 'Physical'

        mock_resource_compare.return_value = False
        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_connections = [CONNECTION_1, CONNECTION_2]
        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0][KEY_CONNECTIONS], expected_connections)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_remove_serial_number_before_update_when_serial_number_type_is_virtual(self,
                                                                                              mock_resource_compare):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_SERIAL_NUMBER_TYPE] = 'Virtual'
        params['data'][KEY_UUID] = 'eb0e2fac-bbe5-4ad1-84d3-3e38481c9806'
        params['data'][KEY_SERIAL_NUMBER] = 'VCGNC3V000'

        mock_resource_compare.return_value = False
        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0][KEY_UUID], 'eb0e2fac-bbe5-4ad1-84d3-3e38481c9806')
        self.assertEqual(args[0][KEY_SERIAL_NUMBER], 'VCGNC3V000')

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_remove_serial_number_before_update_when_serial_number_type_is_physical(self,
                                                                                               mock_resource_compare):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_SERIAL_NUMBER_TYPE] = 'Physical'
        params['data'][KEY_UUID] = 'eb0e2fac-bbe5-4ad1-84d3-3e38481c9806'
        params['data'][KEY_SERIAL_NUMBER] = 'VCGNC3V000'

        mock_resource_compare.return_value = False
        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0][KEY_UUID], 'eb0e2fac-bbe5-4ad1-84d3-3e38481c9806')
        self.assertEqual(args[0][KEY_SERIAL_NUMBER], 'VCGNC3V000')

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_remove_wwpn_from_conns_before_update_when_wwpn_is_virtual(self, mock_resource_compare):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [CONNECTION_1_WITH_WWPN]

        mock_resource_compare.return_value = False
        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_connections = [CONNECTION_1_WITH_WWPN]
        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0][KEY_CONNECTIONS], expected_connections)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_remove_wwpn_from_conns_before_update_when_wwpn_is_physical(self, mock_resource_compare):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_CONNECTIONS] = [CONNECTION_2_WITH_WWPN]

        mock_resource_compare.return_value = False
        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_connections = [CONNECTION_2_WITH_WWPN]
        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0][KEY_CONNECTIONS], expected_connections)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_remove_drive_number_from_controller_drives_before_update(self, mock_resource_compare):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_LOCAL_STORAGE] = dict(controllers=[CONTROLLER_EMBEDDED.copy()])

        mock_resource_compare.return_value = False
        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        expected_drives = DRIVES_CONTROLLER_EMBEDDED
        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0][KEY_LOCAL_STORAGE][KEY_CONTROLLERS][0][KEY_LOGICAL_DRIVES], expected_drives)

    @mock.patch('oneview_server_profile.resource_compare')
    def test_should_not_remove_lun_from_san_volumes_before_update_when_luntype_is_auto(self,
                                                                                       mock_resource_compare):
        params = deepcopy(PARAMS_FOR_PRESENT)
        params['data'][KEY_SAN] = SAN_STORAGE

        mock_resource_compare.return_value = False
        self.mock_ov_client.server_profiles.get_by_name.return_value = deepcopy(BASIC_PROFILE)
        self.mock_ansible_module.params = deepcopy(params)

        ServerProfileModule().run()

        args, _ = self.mock_ov_client.server_profiles.update.call_args
        self.assertEqual(args[0][KEY_SAN][KEY_VOLUMES][0], VOLUME_1)
        self.assertEqual(args[0][KEY_SAN][KEY_VOLUMES][1], VOLUME_2)

    def test_should_do_nothing_when_server_hardware_already_absent(self):
        self.mock_ov_client.server_profiles.get_by_name.return_value = None
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}

        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_ABSENT)

        ServerProfileModule().run()

        self.mock_ov_client.server_profiles.delete.not_been_called()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            msg=SERVER_PROFILE_ALREADY_ABSENT
        )

    def test_should_turn_off_hardware_before_delete(self):
        sh_uri = '/rest/server-hardware/37333036-3831-76jh-4831-303658389766'
        profile_data = deepcopy(BASIC_PROFILE)
        profile_data['serverHardwareUri'] = sh_uri

        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}

        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_ABSENT)

        ServerProfileModule().run()

        self.mock_ov_client.server_hardware.update_power_state.assert_called_once_with(
            {'powerControl': 'PressAndHold', 'powerState': 'Off'}, sh_uri)

        self.mock_ov_client.server_profiles.delete.assert_called_once_with(profile_data)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_DELETED
        )

    def test_should_not_turn_off_hardware_if_not_associated_before_delete(self):
        profile_data = deepcopy(BASIC_PROFILE)

        self.mock_ov_client.server_profiles.get_by_name.return_value = profile_data

        self.mock_ansible_module.params = deepcopy(PARAMS_FOR_ABSENT)

        ServerProfileModule().run()

        times_power_off_was_called = self.mock_ov_client.server_hardware.update_power_state.call_count
        self.assertEqual(0, times_power_off_was_called)

        self.mock_ov_client.server_profiles.delete.assert_called_once_with(profile_data)

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=SERVER_PROFILE_DELETED
        )


class ServerProfileMergerSpec(unittest.TestCase, PreloadedMocksBaseTestCase):
    profile_with_san_storage = CREATED_BASIC_PROFILE.copy()
    profile_with_san_storage[KEY_CONNECTIONS] = [CONNECTION_1, CONNECTION_2]
    profile_with_san_storage[KEY_SAN] = SAN_STORAGE

    profile_with_os_deployment = CREATED_BASIC_PROFILE.copy()
    profile_with_os_deployment[KEY_OS_DEPLOYMENT] = OS_DEPLOYMENT_SETTINGS

    profile_with_local_storage = CREATED_BASIC_PROFILE.copy()
    profile_with_local_storage[KEY_LOCAL_STORAGE] = dict()
    profile_with_local_storage[KEY_LOCAL_STORAGE][KEY_SAS_LOGICAL_JBODS] = [SAS_LOGICAL_JBOD_2, SAS_LOGICAL_JBOD_1]
    profile_with_local_storage[KEY_LOCAL_STORAGE][KEY_CONTROLLERS] = [CONTROLLER_MEZZ_1, CONTROLLER_EMBEDDED]

    def setUp(self):
        self.configure_mocks(self, ServerProfileModule)
        self.mock_ov_client.server_hardware.get_by.return_value = [FAKE_SERVER_HARDWARE]
        self.mock_ov_client.server_hardware.update_power_state.return_value = {}
        self.mock_ov_client.server_profiles.update.return_value = deepcopy(self.profile_with_san_storage)

    def test_merge_when_connections_have_new_item(self):
        connection_added = dict(id=3, name="new-connection")
        data = dict(name="Profile101",
                    connections=[CONN_1_NO_MAC_BASIC_BOOT.copy(),
                                 CONN_2_NO_MAC_BASIC_BOOT.copy(),
                                 connection_added.copy()])
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_connections = [CONNECTION_1.copy(), CONNECTION_2.copy(), connection_added]
        self.assertEqual(merged_data[KEY_CONNECTIONS], expected_connections)

    def test_merge_when_connections_have_removed_item(self):
        data = dict(name="Profile101",
                    connections=[CONNECTION_1.copy()])
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_connections = [CONNECTION_1]
        self.assertEqual(merged_data[KEY_CONNECTIONS], expected_connections)

    def test_merge_when_connections_have_changed_item(self):
        connection_2_renamed = dict(id=2, name="connection-2-renamed", boot=dict(priority="NotBootable"))
        data = dict(name="Profile101",
                    connections=[CONNECTION_1.copy(), connection_2_renamed.copy()])
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        connection_2_merged = dict(id=2, name="connection-2-renamed", mac="E2:4B:0D:30:00:2A", boot=BOOT_CONN)
        expected_connections = [CONNECTION_1.copy(), connection_2_merged.copy()]
        self.assertEqual(merged_data[KEY_CONNECTIONS], expected_connections)

    def test_merge_when_connection_list_is_removed(self):
        data = dict(name="Profile101",
                    connections=[])
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_CONNECTIONS])

    def test_merge_when_connection_list_is_null(self):
        data = dict(name="Profile101",
                    connections=None)
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_CONNECTIONS])

    def test_merge_when_connection_list_not_provided(self):
        data = dict(name="Profile101")

        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_connections = [CONNECTION_1.copy(), CONNECTION_2.copy()]
        self.assertEqual(merged_data[KEY_CONNECTIONS], expected_connections)

    def test_merge_when_existing_connection_list_is_null(self):
        data = dict(name="Profile101",
                    connections=[CONNECTION_1.copy(), CONNECTION_2.copy()])

        resource = deepcopy(self.profile_with_san_storage)
        resource[KEY_CONNECTIONS] = None

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_connections = [CONNECTION_1.copy(), CONNECTION_2.copy()]
        self.assertEqual(merged_data[KEY_CONNECTIONS], expected_connections)

    def test_merge_when_san_storage_is_equals(self):
        data = dict(name="Profile101",
                    connections=[CONNECTION_1.copy(), CONNECTION_2.copy()])
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertEqual(merged_data, resource)

    def test_merge_when_san_storage_has_changes(self):
        data = dict(name="Profile101",
                    sanStorage=deepcopy(SAN_STORAGE))
        data[KEY_SAN].pop('hostOSType')
        data[KEY_SAN]['newField'] = "123"
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_san_storage = deepcopy(SAN_STORAGE)
        expected_san_storage['newField'] = "123"
        self.assertEqual(merged_data[KEY_SAN], expected_san_storage)

    def test_merge_when_san_storage_is_removed_from_profile_with_san(self):
        data = dict(name="Profile101",
                    sanStorage=None)
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_san_storage = dict(manageSanStorage=False,
                                    volumeAttachments=[])
        self.assertEqual(merged_data[KEY_SAN], expected_san_storage)

    def test_merge_when_san_storage_is_removed_from_basic_profile(self):
        data = dict(name="Profile101",
                    sanStorage=None,
                    newField="123")
        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_SAN])

    def test_merge_when_san_storage_not_provided(self):
        data = dict(name="Profile101")
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertEqual(merged_data[KEY_SAN], resource[KEY_SAN])

    def test_merge_when_existing_san_storage_is_null(self):
        data = dict(name="Profile101",
                    sanStorage=deepcopy(SAN_STORAGE))
        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertEqual(merged_data[KEY_SAN], SAN_STORAGE)

    def test_merge_when_volume_attachments_are_removed(self):
        data = dict(name="Profile101",
                    sanStorage=deepcopy(SAN_STORAGE))
        data[KEY_SAN][KEY_VOLUMES] = None
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_SAN][KEY_VOLUMES])

    def test_merge_when_volume_attachments_has_changes(self):
        data = dict(name="Profile101",
                    sanStorage=deepcopy(SAN_STORAGE))
        data[KEY_SAN][KEY_VOLUMES][0]['newField'] = "123"
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_volumes = [deepcopy(VOLUME_1), deepcopy(VOLUME_2)]
        expected_volumes[0]['newField'] = "123"
        self.assertEqual(merged_data[KEY_SAN][KEY_VOLUMES], expected_volumes)

    def test_merge_when_storage_paths_has_changes(self):
        data = dict(name="Profile101",
                    sanStorage=deepcopy(SAN_STORAGE))
        data[KEY_SAN][KEY_VOLUMES][0][KEY_PATHS][1]['newField'] = "123"
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)
        merged_volumes = merged_data[KEY_SAN].get(KEY_VOLUMES)

        expected_paths_storage_1 = [deepcopy(PATH_1), deepcopy(PATH_2)]
        expected_paths_storage_1[1]['newField'] = "123"
        self.assertEqual(expected_paths_storage_1, merged_volumes[0][KEY_PATHS])
        self.assertEqual([], merged_volumes[1][KEY_PATHS])

    def test_merge_should_sort_paths_by_connection_id(self):
        profile = deepcopy(self.profile_with_san_storage)
        profile[KEY_SAN][KEY_VOLUMES][0][KEY_PATHS][0] = deepcopy(PATH_2)  # connectionId = 2
        profile[KEY_SAN][KEY_VOLUMES][0][KEY_PATHS][1] = deepcopy(PATH_1)  # connectionId = 1

        data = dict(name="Profile101",
                    sanStorage=deepcopy(SAN_STORAGE))
        data[KEY_SAN][KEY_VOLUMES][0][KEY_PATHS][0]['newField'] = "123"  # connectionId = 1
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)
        merged_volumes = merged_data[KEY_SAN].get(KEY_VOLUMES)

        path_1_changed = deepcopy(PATH_1)
        path_1_changed['newField'] = "123"
        expected_paths = [deepcopy(path_1_changed),  # connectionId = 1, with field added
                          deepcopy(PATH_2)]  # connectionId = 2
        self.assertEqual(expected_paths, merged_volumes[0][KEY_PATHS])
        self.assertEqual([], merged_volumes[1][KEY_PATHS])

    def test_merge_when_storage_paths_are_removed(self):
        data = dict(name="Profile101",
                    sanStorage=deepcopy(SAN_STORAGE))
        data[KEY_SAN][KEY_VOLUMES][0][KEY_PATHS] = []
        resource = deepcopy(self.profile_with_san_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)
        merged_volumes = merged_data[KEY_SAN].get(KEY_VOLUMES)

        self.assertEqual([], merged_volumes[1][KEY_PATHS])

    def test_merge_when_bios_has_changes(self):
        data = dict(name="Profile101")
        data[KEY_BIOS] = dict(newField="123")
        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_bios = dict(manageBios=False, overriddenSettings=[], newField="123")
        self.assertEqual(merged_data[KEY_BIOS], expected_bios)

    def test_merge_when_bios_is_null(self):
        data = dict(name="Profile101")
        data[KEY_BIOS] = None

        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_BIOS])

    def test_merge_when_bios_not_provided(self):
        data = dict(name="Profile101")
        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_bios = dict(manageBios=False, overriddenSettings=[])
        self.assertEqual(merged_data[KEY_BIOS], expected_bios)

    def test_merge_when_existing_bios_is_null(self):
        data = dict(name="Profile101")
        data[KEY_BIOS] = dict(newField="123")
        resource = deepcopy(CREATED_BASIC_PROFILE)
        resource[KEY_BIOS] = None

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertEqual(merged_data[KEY_BIOS], dict(newField="123"))

    def test_merge_when_boot_has_changes(self):
        data = dict(name="Profile101")
        data[KEY_BOOT] = dict(newField="123")
        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_boot = dict(manageBoot=False, order=[], newField="123")
        self.assertEqual(merged_data[KEY_BOOT], expected_boot)

    def test_merge_when_boot_is_null(self):
        data = dict(name="Profile101")
        data[KEY_BOOT] = None

        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_BOOT])

    def test_merge_when_boot_not_provided(self):
        data = dict(name="Profile101")
        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_boot = dict(manageBoot=False, order=[])
        self.assertEqual(merged_data[KEY_BOOT], expected_boot)

    def test_merge_when_existing_boot_is_null(self):
        data = dict(name="Profile101")
        data[KEY_BOOT] = dict(newField="123")
        resource = deepcopy(CREATED_BASIC_PROFILE)
        resource[KEY_BOOT] = None

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertEqual(merged_data[KEY_BOOT], dict(newField="123"))

    def test_merge_when_boot_mode_has_changes(self):
        data = dict(name="Profile101")
        data[KEY_BOOT_MODE] = dict(newField="123")
        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_boot_mode = dict(manageMode=False, mode=None, pxeBootPolicy=None, newField="123")
        self.assertEqual(merged_data[KEY_BOOT_MODE], expected_boot_mode)

    def test_merge_when_boot_mode_is_null(self):
        data = dict(name="Profile101")
        data[KEY_BOOT_MODE] = None

        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_BOOT_MODE])

    def test_merge_when_boot_mode_not_provided(self):
        data = dict(name="Profile101")
        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_boot_mode = dict(manageMode=False, mode=None, pxeBootPolicy=None)
        self.assertEqual(merged_data[KEY_BOOT_MODE], expected_boot_mode)

    def test_merge_when_existing_boot_mode_is_null(self):
        data = dict(name="Profile101")
        data[KEY_BOOT_MODE] = dict(newField="123")
        resource = deepcopy(CREATED_BASIC_PROFILE)
        resource[KEY_BOOT_MODE] = None

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertEqual(merged_data[KEY_BOOT_MODE], dict(newField="123"))

    def test_merge_when_os_deployment_is_equals(self):
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))
        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertEqual(merged_data, resource)

    def test_merge_when_os_deployment_has_changes(self):
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))
        data[KEY_OS_DEPLOYMENT]['osDeploymentPlanUri'] = "/rest/os-deployment-plans/other-id"
        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_os_deployment = deepcopy(OS_DEPLOYMENT_SETTINGS)
        expected_os_deployment['osDeploymentPlanUri'] = "/rest/os-deployment-plans/other-id"
        self.assertEqual(merged_data[KEY_OS_DEPLOYMENT], expected_os_deployment)

    def test_merge_when_os_deployment_not_provided(self):
        data = dict(name="Profile101")

        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_os_deployment = resource[KEY_OS_DEPLOYMENT]
        self.assertEqual(merged_data[KEY_OS_DEPLOYMENT], expected_os_deployment)

    def test_merge_when_existing_os_deployment_settings_are_null(self):
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))

        resource = deepcopy(self.profile_with_os_deployment)
        resource[KEY_OS_DEPLOYMENT] = None

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_os_deployment = deepcopy(OS_DEPLOYMENT_SETTINGS)
        self.assertEqual(merged_data[KEY_OS_DEPLOYMENT], expected_os_deployment)

    def test_merge_when_custom_attributes_have_changes(self):
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))
        data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES][0]['hostname'] = 'updatedhostname'
        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_os_deployment = deepcopy(OS_DEPLOYMENT_SETTINGS)
        expected_os_deployment[KEY_ATTRIBUTES][0]['hostname'] = 'updatedhostname'
        self.assertEqual(merged_data[KEY_OS_DEPLOYMENT], expected_os_deployment)

    def test_merge_when_custom_attributes_have_new_item(self):
        new_item = dict(name="password", value="secret123")
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))
        data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES].append(new_item.copy())

        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_os_deployment = deepcopy(OS_DEPLOYMENT_SETTINGS)
        expected_os_deployment[KEY_ATTRIBUTES].append(new_item.copy())
        self.assertEqual(merged_data[KEY_OS_DEPLOYMENT], expected_os_deployment)

    def test_merge_when_custom_attributes_have_removed_item(self):
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))
        data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES].pop()
        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_os_deployment = deepcopy(OS_DEPLOYMENT_SETTINGS)
        expected_os_deployment[KEY_ATTRIBUTES].pop()
        self.assertEqual(merged_data[KEY_OS_DEPLOYMENT], expected_os_deployment)

    def test_merge_when_custom_attributes_are_equals_with_different_order(self):
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))
        first_attr = data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES][0]
        second_attr = data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES][1]
        data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES][0] = second_attr
        data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES][1] = first_attr
        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertEqual(merged_data, deepcopy(self.profile_with_os_deployment))

    def test_merge_when_custom_attributes_have_different_values_and_order(self):
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))

        first_attr = data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES][0]
        second_attr = data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES][1]

        first_attr['value'] = 'newValue'
        data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES][0] = second_attr
        data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES][1] = first_attr
        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_os_attributes = [dict(name="username", value="administrator"),
                                  dict(name="hostname", value="newValue")]
        expected_os_deployment = deepcopy(OS_DEPLOYMENT_SETTINGS)
        expected_os_deployment[KEY_ATTRIBUTES] = expected_os_attributes
        self.assertEqual(merged_data[KEY_OS_DEPLOYMENT], expected_os_deployment)

    def test_merge_when_custom_attributes_are_removed(self):
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))
        data[KEY_OS_DEPLOYMENT][KEY_ATTRIBUTES] = None
        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_os_deployment = deepcopy(OS_DEPLOYMENT_SETTINGS)
        expected_os_deployment[KEY_ATTRIBUTES] = None
        self.assertEqual(merged_data[KEY_OS_DEPLOYMENT], expected_os_deployment)

    def test_merge_when_existing_custom_attributes_are_null(self):
        data = dict(name="Profile101",
                    osDeploymentSettings=deepcopy(OS_DEPLOYMENT_SETTINGS))
        resource = deepcopy(self.profile_with_os_deployment)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_attributes = deepcopy(OS_DEPLOYMENT_SETTINGS).get(KEY_ATTRIBUTES)
        self.assertEqual(merged_data[KEY_OS_DEPLOYMENT].get(KEY_ATTRIBUTES), expected_attributes)

    def test_merge_when_local_storage_removed(self):
        data = dict(name="Profile101",
                    localStorage=None)
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertEqual(merged_data[KEY_LOCAL_STORAGE], dict(sasLogicalJBODs=[], controllers=[]))

    def test_merge_when_local_storage_is_null_and_existing_server_profile_is_basic(self):
        data = dict(name="Profile101",
                    localStorage=None)
        resource = deepcopy(CREATED_BASIC_PROFILE)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_LOCAL_STORAGE])

    def test_merge_when_sas_logical_jbods_have_new_item(self):
        sas_logical_jbod_added = dict(id=3, deviceSlot="Mezz 1", name="new-sas-logical-jbod", driveTechnology="SataHdd")
        data = dict(name="Profile101",
                    localStorage=dict(sasLogicalJBODs=[SAS_LOGICAL_JBOD_1.copy(),
                                                       SAS_LOGICAL_JBOD_2.copy(),
                                                       sas_logical_jbod_added.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_sas_logical_jbods = [SAS_LOGICAL_JBOD_1.copy(), SAS_LOGICAL_JBOD_2.copy(), sas_logical_jbod_added]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_SAS_LOGICAL_JBODS], expected_sas_logical_jbods)

    def test_merge_when_sas_logical_jbods_have_removed_item(self):
        data = dict(name="Profile101",
                    localStorage=dict(sasLogicalJBODs=[SAS_LOGICAL_JBOD_1.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_sas_logical_jbods = [SAS_LOGICAL_JBOD_1.copy()]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_SAS_LOGICAL_JBODS], expected_sas_logical_jbods)

    def test_merge_when_sas_logical_jbods_have_changed_item(self):
        item_2_changed = dict(id=2, numPhysicalDrives=2)
        data = dict(name="Profile101",
                    localStorage=dict(sasLogicalJBODs=[SAS_LOGICAL_JBOD_1.copy(), item_2_changed.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        item_2_merged = dict(numPhysicalDrives=2,
                             id=2, name="jbod-2", deviceSlot="Mezz 1", driveTechnology="SataHdd", status="Pending")
        expected_sas_logical_jbods = [SAS_LOGICAL_JBOD_1.copy(), item_2_merged.copy()]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_SAS_LOGICAL_JBODS], expected_sas_logical_jbods)

    def test_merge_should_sort_sas_logical_jbods_by_id(self):
        data = dict(name="Profile101",
                    localStorage=dict(sasLogicalJBODs=[SAS_LOGICAL_JBOD_2.copy(),  # id = 2
                                                       SAS_LOGICAL_JBOD_1.copy()]))  # id = 1
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_sas_logical_jbods = [SAS_LOGICAL_JBOD_1.copy(),  # id = 1
                                      SAS_LOGICAL_JBOD_2.copy()]  # id = 2
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_SAS_LOGICAL_JBODS], expected_sas_logical_jbods)

    @mock.patch('oneview_server_profile.merge_list_by_key')
    def test_merge_should_ignore_logical_jbod_uri_when_null(self, mock_merge_list):
        data = dict(name="Profile101",
                    localStorage=dict(sasLogicalJBODs=[SAS_LOGICAL_JBOD_1.copy(), SAS_LOGICAL_JBOD_2.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        ServerProfileMerger().merge_data(resource, data)

        mock_merge_list.assert_called_once_with(mock.ANY, mock.ANY, key=mock.ANY,
                                                ignore_when_null=[KEY_SAS_LOGICAL_JBOD_URI])

    def test_merge_when_sas_logical_jbod_list_is_removed(self):
        data = dict(name="Profile101",
                    localStorage=dict(sasLogicalJBODs=[]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_LOCAL_STORAGE][KEY_SAS_LOGICAL_JBODS])

    def test_merge_when_controllers_have_new_item(self):
        controller_added = dict(deviceSlot="Device Slot Name", mode="RAID", initialize=False, importConfiguration=True)
        data = dict(name="Profile101",
                    localStorage=dict(controllers=[CONTROLLER_MEZZ_1.copy(),
                                                   CONTROLLER_EMBEDDED.copy(),
                                                   controller_added.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_controllers = [controller_added, CONTROLLER_EMBEDDED.copy(), CONTROLLER_MEZZ_1.copy()]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS], expected_controllers)

    def test_merge_when_controllers_have_removed_item(self):
        data = dict(name="Profile101",
                    localStorage=dict(controllers=[CONTROLLER_MEZZ_1.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_controllers = [CONTROLLER_MEZZ_1.copy()]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS], expected_controllers)

    def test_merge_when_controllers_have_changed_item(self):
        controller_embedded_changed = dict(deviceSlot="Embedded", initialize=True)
        data = dict(name="Profile101",
                    localStorage=dict(controllers=[CONTROLLER_MEZZ_1.copy(),
                                                   controller_embedded_changed.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        item_2_merged = dict(initialize=True,  # initialize value changed from False to True
                             deviceSlot="Embedded", mode="RAID", importConfiguration=True,
                             logicalDrives=DRIVES_CONTROLLER_EMBEDDED)
        expected_controllers = [item_2_merged.copy(), CONTROLLER_MEZZ_1.copy()]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS], expected_controllers)

    def test_merge_when_controller_list_is_removed(self):
        data = dict(name="Profile101",
                    localStorage=dict(controllers=[]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS])

    def test_merge_when_drives_from_embedded_controller_have_new_item(self):
        new_drive = dict(name="drive-3", raidLevel="RAID1", bootable=False, sasLogicalJBODId=None)
        controller_embedded = deepcopy(CONTROLLER_EMBEDDED)
        controller_embedded[KEY_LOGICAL_DRIVES].append(new_drive.copy())

        data = dict(name="Profile101",
                    localStorage=dict(controllers=[CONTROLLER_MEZZ_1.copy(),
                                                   controller_embedded.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_drives = [CONTROLLER_EMBEDDED[KEY_LOGICAL_DRIVES][0],
                           CONTROLLER_EMBEDDED[KEY_LOGICAL_DRIVES][1],
                           new_drive]

        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS][INDEX_EMBED][KEY_LOGICAL_DRIVES],
                         expected_drives)

    def test_merge_when_drives_from_embedded_controller_have_removed_item(self):
        controller_embedded = deepcopy(CONTROLLER_EMBEDDED)
        controller_embedded[KEY_LOGICAL_DRIVES].pop()

        data = dict(name="Profile101",
                    localStorage=dict(controllers=[CONTROLLER_MEZZ_1.copy(),
                                                   controller_embedded.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_drives = [CONTROLLER_EMBEDDED[KEY_LOGICAL_DRIVES][0]]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS][INDEX_EMBED][KEY_LOGICAL_DRIVES],
                         expected_drives)

    def test_merge_when_drives_from_embedded_controller_have_changed_item(self):
        """
        Test the drive merge, although it's not supported by OneView.
        """
        drive_changed = dict(name="drive-1", raidLevel="RAID0")
        controller_embedded = deepcopy(CONTROLLER_EMBEDDED)
        controller_embedded[KEY_LOGICAL_DRIVES][0] = drive_changed

        data = dict(name="Profile101",
                    localStorage=dict(controllers=[CONTROLLER_MEZZ_1.copy(),
                                                   controller_embedded.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        drive_1_merged = dict(driveNumber=1, name="drive-1", raidLevel="RAID0", bootable=False, sasLogicalJBODId=None)
        expected_drives = [drive_1_merged,
                           CONTROLLER_EMBEDDED[KEY_LOGICAL_DRIVES][1]]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS][INDEX_EMBED][KEY_LOGICAL_DRIVES],
                         expected_drives)

    def test_merge_when_drives_from_mezz_controller_have_new_item(self):
        new_drive = dict(name=None, raidLevel="RAID1", bootable=False, sasLogicalJBODId=3)
        controller_mezz = deepcopy(CONTROLLER_MEZZ_1)
        controller_mezz[KEY_LOGICAL_DRIVES].append(new_drive)

        data = dict(name="Profile101",
                    localStorage=dict(controllers=[controller_mezz.copy(),
                                                   CONTROLLER_EMBEDDED.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_drives = [CONTROLLER_MEZZ_1[KEY_LOGICAL_DRIVES][0],
                           CONTROLLER_MEZZ_1[KEY_LOGICAL_DRIVES][1],
                           new_drive]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS][INDEX_MEZZ][KEY_LOGICAL_DRIVES],
                         expected_drives)

    def test_merge_when_drives_from_mezz_controller_have_removed_item(self):
        controller_mezz = deepcopy(CONTROLLER_MEZZ_1)
        controller_mezz[KEY_LOGICAL_DRIVES].pop()

        data = dict(name="Profile101",
                    localStorage=dict(controllers=[controller_mezz.copy(),
                                                   CONTROLLER_EMBEDDED.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        expected_drives = [CONTROLLER_MEZZ_1[KEY_LOGICAL_DRIVES][0]]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS][INDEX_MEZZ][KEY_LOGICAL_DRIVES],
                         expected_drives)

    def test_merge_when_drives_from_mezz_controller_have_changed_item(self):
        """
        Test the drive merge, although it's not supported by OneView.
        """
        drive_changed = dict(sasLogicalJBODId=1, raidLevel="RAID0")
        controller_mezz = deepcopy(CONTROLLER_MEZZ_1)
        controller_mezz[KEY_LOGICAL_DRIVES][0] = drive_changed

        data = dict(name="Profile101",
                    localStorage=dict(controllers=[controller_mezz.copy(),
                                                   CONTROLLER_EMBEDDED.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        drive_1_merged = dict(name=None, raidLevel="RAID0", bootable=False, sasLogicalJBODId=1)
        expected_drives = [drive_1_merged,
                           CONTROLLER_MEZZ_1[KEY_LOGICAL_DRIVES][1]]
        self.assertEqual(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS][INDEX_MEZZ][KEY_LOGICAL_DRIVES],
                         expected_drives)

    def test_merge_when_controller_drives_are_removed(self):
        controller_mezz = deepcopy(CONTROLLER_MEZZ_1)
        controller_mezz[KEY_LOGICAL_DRIVES] = []

        data = dict(name="Profile101",
                    localStorage=dict(controllers=[controller_mezz.copy(),
                                                   CONTROLLER_EMBEDDED.copy()]))
        resource = deepcopy(self.profile_with_local_storage)

        merged_data = ServerProfileMerger().merge_data(resource, data)

        self.assertFalse(merged_data[KEY_LOCAL_STORAGE][KEY_CONTROLLERS][INDEX_MEZZ][KEY_LOGICAL_DRIVES])


if __name__ == '__main__':
    unittest.main()
