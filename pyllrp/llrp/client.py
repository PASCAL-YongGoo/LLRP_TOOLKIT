"""
High-level LLRP Client Implementation
"""

import time
import logging
from typing import Optional, List, Dict, Callable
from threading import Lock
from .protocol import LLRPConnection, MessageType
from .messages import (
    GetReaderCapabilities, GetReaderCapabilitiesResponse,
    GetReaderConfig, GetReaderConfigResponse,
    SetReaderConfig, SetReaderConfigResponse,
    EnableEventsAndReports, ReaderEventNotification,
    AddROSpec, EnableROSpec, StartROSpec, StopROSpec, DeleteROSpec,
    AddAccessSpec, EnableAccessSpec, DisableAccessSpec, DeleteAccessSpec, GetAccessSpecs,
    ROSpec, ROBoundarySpec, ROSpecStartTrigger, ROSpecStopTrigger,
    AISpec, AISpecStopTrigger, InventoryParameterSpec,
    ROReportSpec, TagReportContentSelector,
    ROAccessReport
)

logger = logging.getLogger(__name__)


class LLRPClient:
    """High-level LLRP Client for RFID readers"""
    
    def __init__(self, host: str, port: int = 5084):
        """
        Initialize LLRP Client
        
        Args:
            host: Reader IP address or hostname
            port: LLRP port (default 5084)
        """
        self.host = host
        self.port = port
        self.connection = LLRPConnection(host, port)
        self.current_rospec_id = 1
        self.tag_callback: Optional[Callable] = None
        self.event_callback: Optional[Callable] = None
        self.tags_read: List[Dict] = []
        self.tags_lock = Lock()
        
        # Setup message handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup internal message handlers"""
        self.connection.add_message_handler(
            MessageType.RO_ACCESS_REPORT,
            self._handle_tag_report
        )
        self.connection.add_message_handler(
            MessageType.READER_EVENT_NOTIFICATION,
            self._handle_reader_event
        )
    
    def _handle_tag_report(self, message: ROAccessReport):
        """Handle incoming tag reports with complete parsing"""
        with self.tags_lock:
            for tag_data in message.tag_report_data:
                tag_info = {
                    'epc': tag_data.get_epc_hex(),
                    'antenna_id': tag_data.antenna_id,
                    'rssi': tag_data.peak_rssi,
                    'channel_index': tag_data.channel_index,
                    'first_seen_utc': tag_data.first_seen_timestamp_utc,
                    'first_seen_uptime': tag_data.first_seen_timestamp_uptime,
                    'last_seen_utc': tag_data.last_seen_timestamp_utc,
                    'last_seen_uptime': tag_data.last_seen_timestamp_uptime,
                    'seen_count': tag_data.tag_seen_count,
                    'rospec_id': tag_data.rospec_id,
                    'spec_index': tag_data.spec_index,
                    'inventory_param_spec_id': tag_data.inventory_parameter_spec_id,
                    'access_spec_id': tag_data.access_spec_id,
                    'timestamp': time.time()
                }
                
                # Add convenience fields
                tag_info['first_seen'] = tag_data.get_first_seen_timestamp()
                tag_info['last_seen'] = tag_data.get_last_seen_timestamp()
                
                self.tags_read.append(tag_info)
                
                # Call user callback if set
                if self.tag_callback:
                    try:
                        self.tag_callback(tag_info)
                    except Exception as e:
                        logger.error(f"Tag callback error: {e}")
    
    def _handle_reader_event(self, message: ReaderEventNotification):
        """Handle reader event notifications"""
        if not message.reader_event_notification_data:
            return
        
        event_data = message.reader_event_notification_data
        
        # Create event info dictionary
        event_info = {
            'timestamp': time.time(),
            'message_id': message.msg_id,
            'events': []
        }
        
        # Parse different event types
        if event_data.connection_attempt_event:
            event_info['events'].append({
                'type': 'connection_attempt',
                'status': event_data.connection_attempt_event.status,
                'description': 'Success' if event_data.connection_attempt_event.status == 0 else 'Failed - Reader connection exists'
            })
        
        if event_data.connection_close_event:
            event_info['events'].append({
                'type': 'connection_close',
                'description': 'Connection closed by reader'
            })
        
        if event_data.antenna_event:
            event_info['events'].append({
                'type': 'antenna_event',
                'antenna_id': event_data.antenna_event.antenna_id,
                'event_type': event_data.antenna_event.event_type,
                'description': 'Connected' if event_data.antenna_event.event_type == 1 else 'Disconnected'
            })
        
        if event_data.reader_exception_event:
            event_info['events'].append({
                'type': 'reader_exception',
                'message': event_data.reader_exception_event.message,
                'op_spec_id': event_data.reader_exception_event.op_spec_id,
                'access_spec_id': event_data.reader_exception_event.access_spec_id
            })
        
        if event_data.rospec_event:
            event_info['events'].append({
                'type': 'rospec_event',
                'event_type': event_data.rospec_event.event_type,
                'rospec_id': event_data.rospec_event.rospec_id,
                'preempting_rospec_id': event_data.rospec_event.preempting_rospec_id,
                'description': 'Start' if event_data.rospec_event.event_type == 0 else 'End'
            })
        
        if event_data.ai_spec_event:
            event_info['events'].append({
                'type': 'ai_spec_event',
                'event_type': event_data.ai_spec_event.event_type,
                'rospec_id': event_data.ai_spec_event.rospec_id,
                'spec_index': event_data.ai_spec_event.spec_index,
                'description': 'End of AISpec'
            })
        
        if event_data.report_buffer_level_warning_event:
            event_info['events'].append({
                'type': 'buffer_warning',
                'buffer_fill_percentage': event_data.report_buffer_level_warning_event.buffer_fill_percentage,
                'description': f'Buffer {event_data.report_buffer_level_warning_event.buffer_fill_percentage}% full'
            })
        
        if event_data.report_buffer_overflow_error_event:
            event_info['events'].append({
                'type': 'buffer_overflow',
                'description': 'Report buffer overflow - some data may be lost'
            })
        
        if event_data.llrp_status:
            event_info['llrp_status'] = event_data.llrp_status.to_dict()
        
        # Log events
        for event in event_info['events']:
            logger.info(f"Reader event: {event['type']} - {event.get('description', 'No description')}")
        
        # Call user event callback if set
        if self.event_callback:
            try:
                self.event_callback(event_info)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
    
    def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to RFID reader
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully
        """
        success = self.connection.connect(timeout)
        if success:
            logger.info(f"Connected to RFID reader at {self.host}:{self.port}")
        else:
            logger.error(f"Failed to connect to {self.host}:{self.port}")
        return success
    
    def disconnect(self):
        """Disconnect from reader with graceful close"""
        try:
            # Try graceful disconnect first
            if self.connection.graceful_disconnect():
                logger.info("Graceful disconnect successful")
            else:
                # Fall back to regular disconnect
                self.connection.disconnect()
                logger.info("Regular disconnect completed")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            # Force disconnect as last resort
            self.connection.disconnect()
    
    def get_capabilities(self) -> Optional[Dict]:
        """
        Get reader capabilities with enhanced error handling
        
        Returns:
            Dictionary with reader capabilities or None if failed
        """
        from .errors import check_llrp_response, LLRPError
        
        try:
            msg = GetReaderCapabilities(msg_id=self.connection.next_message_id)
            response = self.connection.send_recv(msg, timeout=10.0)
            
            if not response:
                logger.error("No response to GET_READER_CAPABILITIES")
                return None
                
            if not isinstance(response, GetReaderCapabilitiesResponse):
                logger.error(f"Unexpected response type: {type(response)}")
                return None
            
            # Check LLRP status
            if response.llrp_status:
                check_llrp_response(
                    response.llrp_status.status_code,
                    response.llrp_status.error_description,
                    raise_on_error=True
                )
                
                capabilities_info = {
                    'status': 'success',
                    'llrp_status': response.llrp_status.to_dict()
                }
                
                # Add general device capabilities
                if response.general_device_capabilities:
                    capabilities_info['general_device'] = {
                        'max_antennas': response.general_device_capabilities.max_number_of_antenna_supported,
                        'can_set_antenna_properties': response.general_device_capabilities.can_set_antenna_properties,
                        'has_utc_clock': response.general_device_capabilities.has_utc_clock_capability,
                        'manufacturer': response.general_device_capabilities.device_manufacturer_name,
                        'model': response.general_device_capabilities.model_name,
                        'firmware_version': response.general_device_capabilities.firmware_version,
                    }
                
                # Add LLRP capabilities
                if response.llrp_capabilities:
                    capabilities_info['llrp'] = {
                        'can_do_rf_survey': response.llrp_capabilities.can_do_rf_survey,
                        'can_report_buffer_warning': response.llrp_capabilities.can_report_buffer_fill_warning,
                        'supports_client_request_opspec': response.llrp_capabilities.supports_client_request_opspec,
                        'can_stateaware_singulation': response.llrp_capabilities.can_stateaware_singulation,
                        'supports_holding_events_reports': response.llrp_capabilities.supports_holding_of_events_and_reports,
                        'max_priority_levels': response.llrp_capabilities.max_num_priority_levels_supported,
                        'client_opspec_timeout': response.llrp_capabilities.client_request_opspec_timeout,
                        'max_rospecs': response.llrp_capabilities.max_num_rospecs,
                        'max_spec_params_per_rospec': response.llrp_capabilities.max_num_spec_parameters_per_rospec,
                        'max_inventory_params_per_aispec': response.llrp_capabilities.max_num_inventory_parameter_spec_parameters_per_aispec,
                        'max_access_specs': response.llrp_capabilities.max_num_access_specs,
                        'max_op_specs_per_access_spec': response.llrp_capabilities.max_num_op_specs_per_access_spec,
                    }
                
                # Add regulatory capabilities
                if response.regulatory_capabilities:
                    capabilities_info['regulatory'] = {
                        'country_code': response.regulatory_capabilities.country_code,
                        'communications_standard': response.regulatory_capabilities.communications_standard,
                        'uhf_band_capabilities': len(response.regulatory_capabilities.uhf_band_capabilities),
                    }
                
                # Add air protocol capabilities
                if hasattr(response, 'air_protocol_capabilities') and response.air_protocol_capabilities:
                    capabilities_info['air_protocol'] = []
                    for air_proto in response.air_protocol_capabilities:
                        capabilities_info['air_protocol'].append({
                            'can_support_block_erase': air_proto.can_support_block_erase,
                            'can_support_block_write': air_proto.can_support_block_write,
                            'can_support_block_permalock': air_proto.can_support_block_permalock,
                            'can_support_tag_recommissioning': air_proto.can_support_tag_recommissioning,
                            'can_support_uhf_c1g2_custom_parameters': air_proto.can_support_uhf_c1g2_custom_parameters,
                            'can_support_xpc': air_proto.can_support_xpc,
                            'max_select_filters_per_query': air_proto.max_num_select_filters_per_query,
                        })
                
                return capabilities_info
            else:
                logger.warning("No LLRPStatus in capabilities response")
                return None
                
        except LLRPError as e:
            logger.error(f"LLRP error getting capabilities: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting capabilities: {e}")
            return None
    
    def clear_rospecs(self) -> bool:
        """
        Clear all ROSpecs from reader
        
        Returns:
            True if successful
        """
        msg = DeleteROSpec(
            msg_id=self.connection.next_message_id,
            rospec_id=0  # 0 = delete all
        )
        
        response = self.connection.send_recv(msg, timeout=5.0)
        if response and hasattr(response, 'llrp_status'):
            return response.llrp_status.status_code == 0
        return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def create_basic_rospec(self,
                          rospec_id: int = None,
                          duration_ms: int = 0,
                          antenna_ids: List[int] = None,
                          report_every_n_tags: int = 1,
                          start_immediate: bool = False) -> ROSpec:
        """
        Create a basic ROSpec for inventory
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            duration_ms: Duration in milliseconds (0 = infinite)
            antenna_ids: List of antenna IDs (None = all)
            report_every_n_tags: Report frequency (0 = end of spec only)
            start_immediate: Start immediately when enabled
            
        Returns:
            Configured ROSpec object
        """
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create ROSpec
        rospec = ROSpec(rospec_id=rospec_id, priority=0, current_state=0)
        
        # Configure boundaries
        rospec.ro_boundary_spec = ROBoundarySpec()
        
        # Start trigger
        if start_immediate:
            rospec.ro_boundary_spec.rospec_start_trigger = ROSpecStartTrigger(
                trigger_type=1  # Immediate
            )
        else:
            rospec.ro_boundary_spec.rospec_start_trigger = ROSpecStartTrigger(
                trigger_type=0  # Null (manual start)
            )
        
        # Stop trigger
        if duration_ms > 0:
            rospec.ro_boundary_spec.rospec_stop_trigger = ROSpecStopTrigger(
                trigger_type=1,  # Duration
                duration_ms=duration_ms
            )
        else:
            rospec.ro_boundary_spec.rospec_stop_trigger = ROSpecStopTrigger(
                trigger_type=0  # Null (manual stop)
            )
        
        # AISpec (Antenna Inventory Spec)
        aispec = AISpec(antenna_ids=antenna_ids or [0])
        aispec.ai_spec_stop_trigger = AISpecStopTrigger(trigger_type=0)
        
        # Inventory parameters
        inv_param = InventoryParameterSpec(spec_id=1)
        aispec.inventory_parameter_specs = [inv_param]
        
        rospec.spec_parameters = [aispec]
        
        # Report spec
        if report_every_n_tags > 0:
            rospec.ro_report_spec = ROReportSpec(
                trigger=3,  # N tags or end of ROSpec
                n_value=report_every_n_tags
            )
        else:
            rospec.ro_report_spec = ROReportSpec(
                trigger=1  # End of ROSpec only
            )
        
        # Tag report content
        selector = TagReportContentSelector()
        rospec.ro_report_spec.tag_report_content_selector = selector
        
        return rospec
    
    def add_rospec(self, rospec: ROSpec) -> bool:
        """
        Add ROSpec to reader
        
        Args:
            rospec: ROSpec to add
            
        Returns:
            True if successful
        """
        msg = AddROSpec(
            msg_id=self.connection.next_message_id,
            rospec=rospec
        )
        
        response = self.connection.send_recv(msg, timeout=5.0)
        if response and hasattr(response, 'llrp_status'):
            return response.llrp_status.status_code == 0
        return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def enable_rospec(self, rospec_id: int) -> bool:
        """
        Enable ROSpec
        
        Args:
            rospec_id: ROSpec ID to enable
            
        Returns:
            True if successful
        """
        msg = EnableROSpec(
            msg_id=self.connection.next_message_id,
            rospec_id=rospec_id
        )
        
        response = self.connection.send_recv(msg, timeout=5.0)
        if response and hasattr(response, 'llrp_status'):
            return response.llrp_status.status_code == 0
        return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def start_rospec(self, rospec_id: int) -> bool:
        """
        Start ROSpec
        
        Args:
            rospec_id: ROSpec ID to start
            
        Returns:
            True if successful
        """
        msg = StartROSpec(
            msg_id=self.connection.next_message_id,
            rospec_id=rospec_id
        )
        
        response = self.connection.send_recv(msg, timeout=5.0)
        if response and hasattr(response, 'llrp_status'):
            return response.llrp_status.status_code == 0
        return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def stop_rospec(self, rospec_id: int) -> bool:
        """
        Stop ROSpec
        
        Args:
            rospec_id: ROSpec ID to stop
            
        Returns:
            True if successful
        """
        msg = StopROSpec(
            msg_id=self.connection.next_message_id,
            rospec_id=rospec_id
        )
        
        response = self.connection.send_recv(msg, timeout=5.0)
        if response and hasattr(response, 'llrp_status'):
            return response.llrp_status.status_code == 0
        return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def simple_inventory(self,
                        duration_seconds: float = 5.0,
                        antenna_ids: List[int] = None,
                        tag_callback: Callable = None) -> List[Dict]:
        """
        Perform simple inventory operation
        
        Args:
            duration_seconds: How long to read tags
            antenna_ids: List of antenna IDs (None = all)
            tag_callback: Function called for each tag (tag_info)
            
        Returns:
            List of tags read
        """
        # Clear previous tags
        with self.tags_lock:
            self.tags_read.clear()
        
        # Set callback
        self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create and add ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=123,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=False
        )
        
        if not self.add_rospec(rospec):
            logger.error("Failed to add ROSpec")
            return []
        
        # Enable ROSpec
        if not self.enable_rospec(123):
            logger.error("Failed to enable ROSpec")
            return []
        
        # Start ROSpec
        if not self.start_rospec(123):
            logger.error("Failed to start ROSpec")
            return []
        
        logger.info(f"Starting inventory for {duration_seconds} seconds...")
        
        # Wait for completion
        time.sleep(duration_seconds + 0.5)
        
        # Stop ROSpec (if still running)
        self.stop_rospec(123)
        
        # Clean up
        self.clear_rospecs()
        
        # Return collected tags
        with self.tags_lock:
            return self.tags_read.copy()
    
    def start_continuous_inventory(self,
                                  antenna_ids: List[int] = None,
                                  tag_callback: Callable = None) -> bool:
        """
        Start continuous inventory (runs until stopped)
        
        Args:
            antenna_ids: List of antenna IDs (None = all)
            tag_callback: Function called for each tag
            
        Returns:
            True if started successfully
        """
        # Set callback
        self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create ROSpec with no stop trigger
        rospec = self.create_basic_rospec(
            rospec_id=456,
            duration_ms=0,  # Infinite
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        if not self.add_rospec(rospec):
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
        
        if not self.enable_rospec(456):
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
        
        logger.info("Started continuous inventory")
        return True
    
    def stop_continuous_inventory(self) -> bool:
        """
        Stop continuous inventory
        
        Returns:
            True if stopped successfully
        """
        success = self.stop_rospec(456)
        if success:
            self.clear_rospecs()
            logger.info("Stopped continuous inventory")
        return success
    
    # Reader Configuration Methods
    
    def get_reader_config(self, antenna_id: int = 0, 
                         requested_configuration: int = 0) -> Optional[Dict]:
        """
        Get reader configuration
        
        Args:
            antenna_id: Antenna ID (0 = all antennas)
            requested_configuration: Bitmask of requested config types
            
        Returns:
            Configuration dictionary or None if failed
        """
        from .errors import check_llrp_response, LLRPError
        
        try:
            msg = GetReaderConfig(
                msg_id=self.connection.next_message_id,
                antenna_id=antenna_id,
                requested_configuration=requested_configuration
            )
            
            response = self.connection.send_recv(msg, timeout=10.0)
            
            if not response:
                logger.error("No response to GET_READER_CONFIG")
                return None
                
            if not isinstance(response, GetReaderConfigResponse):
                logger.error(f"Unexpected response type: {type(response)}")
                return None
            
            # Check LLRP status
            if response.llrp_status:
                check_llrp_response(
                    response.llrp_status.status_code,
                    response.llrp_status.error_description,
                    raise_on_error=True
                )
                
                return {
                    'status': 'success',
                    'antenna_configurations': [
                        {
                            'antenna_id': config.antenna_id,
                            'transmit_power': config.get_transmit_power(),
                            'rf_receiver': {
                                'sensitivity': config.rf_receiver.receiver_sensitivity / 100.0
                            } if config.rf_receiver else None,
                            'rf_transmitter': {
                                'power': config.rf_transmitter.get_power_dbm(),
                                'hop_table_id': config.rf_transmitter.hop_table_id,
                                'channel_index': config.rf_transmitter.channel_index
                            } if config.rf_transmitter else None,
                            'antenna_properties': {
                                'connected': config.antenna_properties.antenna_connected,
                                'gain': config.antenna_properties.antenna_gain / 100.0
                            } if config.antenna_properties else None
                        }
                        for config in response.antenna_configurations
                    ],
                    'events_and_reports': {
                        'hold_events_on_reconnect': response.events_and_reports.hold_events_and_reports_upon_reconnect
                    } if response.events_and_reports else None,
                    'keepalive_spec': {
                        'trigger_type': response.keepalive_spec.keepalive_trigger_type,
                        'periodic_value_ms': response.keepalive_spec.periodic_trigger_value
                    } if response.keepalive_spec else None,
                    'llrp_status': response.llrp_status.to_dict()
                }
            else:
                logger.warning("No LLRPStatus in config response")
                return None
                
        except LLRPError as e:
            logger.error(f"LLRP error getting configuration: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting configuration: {e}")
            return None
    
    def set_reader_config(self, reset_to_factory: bool = False,
                         antenna_configs: List[Dict] = None,
                         events_config: Dict = None,
                         keepalive_config: Dict = None) -> bool:
        """
        Set reader configuration
        
        Args:
            reset_to_factory: Reset to factory defaults first
            antenna_configs: List of antenna configuration dictionaries
            events_config: Events and reports configuration
            keepalive_config: Keepalive specification
            
        Returns:
            True if successful
        """
        from .errors import check_llrp_response, LLRPError
        from .config_parameters import (
            AntennaConfiguration, RFTransmitter, RFReceiver,
            EventsAndReports, KeepaliveSpec
        )
        
        try:
            msg = SetReaderConfig(
                msg_id=self.connection.next_message_id,
                reset_to_factory_default=reset_to_factory
            )
            
            # Add antenna configurations
            if antenna_configs:
                for config in antenna_configs:
                    antenna_config = AntennaConfiguration(
                        antenna_id=config.get('antenna_id', 1)
                    )
                    
                    # Add RF transmitter config
                    if 'transmit_power' in config:
                        rf_tx = RFTransmitter(
                            hop_table_id=config.get('hop_table_id', 1),
                            channel_index=config.get('channel_index', 1),
                            transmit_power=int(config['transmit_power'] * 100)
                        )
                        antenna_config.rf_transmitter = rf_tx
                    
                    # Add RF receiver config  
                    if 'receiver_sensitivity' in config:
                        rf_rx = RFReceiver(
                            receiver_sensitivity=int(config['receiver_sensitivity'] * 100)
                        )
                        antenna_config.rf_receiver = rf_rx
                    
                    msg.add_antenna_config(antenna_config)
            
            # Add events and reports config
            if events_config:
                events = EventsAndReports()
                events.hold_events_and_reports_upon_reconnect = events_config.get(
                    'hold_events_on_reconnect', False
                )
                msg.events_and_reports = events
            
            # Add keepalive config
            if keepalive_config:
                keepalive = KeepaliveSpec(
                    keepalive_trigger_type=keepalive_config.get('trigger_type', 1),
                    periodic_trigger_value=keepalive_config.get('periodic_value_ms', 10000)
                )
                msg.keepalive_spec = keepalive
            
            response = self.connection.send_recv(msg, timeout=10.0)
            
            if response and hasattr(response, 'llrp_status'):
                if response.llrp_status:
                    check_llrp_response(
                        response.llrp_status.status_code,
                        response.llrp_status.error_description,
                        raise_on_error=True
                    )
                    logger.info("Reader configuration updated successfully")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to set reader config: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def set_antenna_power(self, antenna_id: int, power_dbm: float) -> bool:
        """
        Set antenna transmit power
        
        Args:
            antenna_id: Antenna ID
            power_dbm: Transmit power in dBm
            
        Returns:
            True if successful
        """
        return self.set_reader_config(
            antenna_configs=[{
                'antenna_id': antenna_id,
                'transmit_power': power_dbm
            }]
        )
    
    def set_antenna_sensitivity(self, antenna_id: int, sensitivity_dbm: float) -> bool:
        """
        Set antenna receiver sensitivity
        
        Args:
            antenna_id: Antenna ID
            sensitivity_dbm: Receiver sensitivity in dBm
            
        Returns:
            True if successful
        """
        return self.set_reader_config(
            antenna_configs=[{
                'antenna_id': antenna_id,
                'receiver_sensitivity': sensitivity_dbm
            }]
        )
    
    def enable_events_and_reports(self, hold_on_reconnect: bool = False) -> bool:
        """
        Configure events and reports
        
        Args:
            hold_on_reconnect: Hold events/reports on reconnection
            
        Returns:
            True if successful
        """
        return self.set_reader_config(
            events_config={
                'hold_events_on_reconnect': hold_on_reconnect
            }
        )
    
    def set_keepalive(self, period_ms: int = 10000) -> bool:
        """
        Set keepalive period
        
        Args:
            period_ms: Keepalive period in milliseconds
            
        Returns:
            True if successful
        """
        return self.set_reader_config(
            keepalive_config={
                'trigger_type': 1,  # Periodic
                'periodic_value_ms': period_ms
            }
        )
    
    def enable_events_and_reports(self, event_callback: Callable = None) -> bool:
        """
        Enable reader events and reports
        
        Args:
            event_callback: Function called for each reader event
            
        Returns:
            True if successful
        """
        from .errors import check_llrp_response, LLRPError
        
        try:
            # Set event callback
            if event_callback:
                self.event_callback = event_callback
            
            # Send ENABLE_EVENTS_AND_REPORTS message
            msg = EnableEventsAndReports(msg_id=self.connection.next_message_id)
            
            # Note: ENABLE_EVENTS_AND_REPORTS doesn't return a response message
            # It just enables the reader to send event notifications
            success = self.connection.send_message(msg)
            
            if success:
                logger.info("Events and reports enabled")
                return True
            else:
                logger.error("Failed to enable events and reports")
                return False
        except Exception as e:
            logger.error(f"Error enabling events: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def set_event_callback(self, callback: Callable):
        """
        Set callback function for reader events
        
        Args:
            callback: Function to call when reader events occur
                     Signature: callback(event_info: Dict)
        """
        self.event_callback = callback
        logger.info("Event callback set")
    
    # AccessSpec Methods
    
    def create_read_access_spec(self, access_spec_id: int, rospec_id: int,
                               antenna_id: int = 0, memory_bank: int = 1,
                               word_pointer: int = 2, word_count: int = 0,
                               access_password: int = 0):
        """
        Create an AccessSpec for reading tag memory
        
        Args:
            access_spec_id: Unique AccessSpec ID
            rospec_id: ROSpec to bind this AccessSpec to
            antenna_id: Antenna ID (0 = all antennas)
            memory_bank: Memory bank (0=Reserved, 1=EPC, 2=TID, 3=User)
            word_pointer: Starting word address
            word_count: Number of words to read (0 = read to end)
            access_password: Access password if needed
            
        Returns:
            AccessSpec object
        """
        from .accessspec_parameters import (
            AccessSpec, AccessCommand, AccessReportSpec, C1G2Read
        )
        
        # Create AccessSpec
        access_spec = AccessSpec(
            access_spec_id=access_spec_id,
            antenna_id=antenna_id,
            protocol_id=1,  # EPC Gen2
            current_state=0  # Disabled
        )
        access_spec.rospec_id = rospec_id
        
        # Create Access Command with C1G2 Read
        access_command = AccessCommand()
        
        read_op = C1G2Read(
            op_spec_id=1,
            access_password=access_password,
            memory_bank=memory_bank,
            word_pointer=word_pointer,
            word_count=word_count
        )
        access_command.access_command_op_specs.append(read_op)
        
        access_spec.access_command = access_command
        
        # Create Access Report Spec
        access_spec.access_report_spec = AccessReportSpec(access_report_trigger=1)
        
        return access_spec
    
    def create_write_access_spec(self, access_spec_id: int, rospec_id: int,
                                antenna_id: int = 0, memory_bank: int = 3,
                                word_pointer: int = 0, write_data: bytes = b'',
                                access_password: int = 0):
        """
        Create an AccessSpec for writing to tag memory
        
        Args:
            access_spec_id: Unique AccessSpec ID
            rospec_id: ROSpec to bind this AccessSpec to
            antenna_id: Antenna ID (0 = all antennas)
            memory_bank: Memory bank (usually 3=User)
            word_pointer: Starting word address
            write_data: Data to write (word-aligned)
            access_password: Access password if needed
            
        Returns:
            AccessSpec object
        """
        from .accessspec_parameters import (
            AccessSpec, AccessCommand, AccessReportSpec, C1G2Write
        )
        
        # Create AccessSpec
        access_spec = AccessSpec(
            access_spec_id=access_spec_id,
            antenna_id=antenna_id,
            protocol_id=1,  # EPC Gen2
            current_state=0  # Disabled
        )
        access_spec.rospec_id = rospec_id
        
        # Create Access Command with C1G2 Write
        access_command = AccessCommand()
        
        write_op = C1G2Write(
            op_spec_id=1,
            access_password=access_password,
            memory_bank=memory_bank,
            word_pointer=word_pointer,
            write_data=write_data
        )
        access_command.access_command_op_specs.append(write_op)
        
        access_spec.access_command = access_command
        
        # Create Access Report Spec
        access_spec.access_report_spec = AccessReportSpec(access_report_trigger=1)
        
        return access_spec
    
    def add_access_spec(self, access_spec) -> bool:
        """
        Add AccessSpec to reader
        
        Args:
            access_spec: AccessSpec object to add
            
        Returns:
            True if successful
        """
        from .errors import check_llrp_response, LLRPError
        
        try:
            msg = AddAccessSpec(
                msg_id=self.connection.next_message_id,
                access_spec=access_spec
            )
            
            response = self.connection.send_recv(msg, timeout=10.0)
            
            if response and hasattr(response, 'llrp_status'):
                if response.llrp_status:
                    check_llrp_response(
                        response.llrp_status.status_code,
                        response.llrp_status.error_description,
                        raise_on_error=True
                    )
                    logger.info(f"AccessSpec {access_spec.access_spec_id} added successfully")
                    return True
                return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
            
        except LLRPError as e:
            logger.error(f"LLRP error adding AccessSpec: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
        except Exception as e:
            logger.error(f"Unexpected error adding AccessSpec: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def enable_access_spec(self, access_spec_id: int) -> bool:
        """
        Enable AccessSpec
        
        Args:
            access_spec_id: AccessSpec ID to enable
            
        Returns:
            True if successful
        """
        from .errors import check_llrp_response, LLRPError
        
        try:
            msg = EnableAccessSpec(
                msg_id=self.connection.next_message_id,
                access_spec_id=access_spec_id
            )
            
            response = self.connection.send_recv(msg, timeout=5.0)
            
            if response and hasattr(response, 'llrp_status'):
                if response.llrp_status:
                    check_llrp_response(
                        response.llrp_status.status_code,
                        response.llrp_status.error_description,
                        raise_on_error=True
                    )
                    logger.info(f"AccessSpec {access_spec_id} enabled")
                    return True
                return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
            
        except LLRPError as e:
            logger.error(f"LLRP error enabling AccessSpec: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
        except Exception as e:
            logger.error(f"Unexpected error enabling AccessSpec: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def disable_access_spec(self, access_spec_id: int) -> bool:
        """
        Disable AccessSpec
        
        Args:
            access_spec_id: AccessSpec ID to disable
            
        Returns:
            True if successful
        """
        from .errors import check_llrp_response, LLRPError
        
        try:
            msg = DisableAccessSpec(
                msg_id=self.connection.next_message_id,
                access_spec_id=access_spec_id
            )
            
            response = self.connection.send_recv(msg, timeout=5.0)
            
            if response and hasattr(response, 'llrp_status'):
                if response.llrp_status:
                    check_llrp_response(
                        response.llrp_status.status_code,
                        response.llrp_status.error_description,
                        raise_on_error=True
                    )
                    logger.info(f"AccessSpec {access_spec_id} disabled")
                    return True
                return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
            
        except LLRPError as e:
            logger.error(f"LLRP error disabling AccessSpec: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
        except Exception as e:
            logger.error(f"Unexpected error disabling AccessSpec: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def delete_access_spec(self, access_spec_id: int = 0) -> bool:
        """
        Delete AccessSpec from reader
        
        Args:
            access_spec_id: AccessSpec ID to delete (0 = delete all)
            
        Returns:
            True if successful
        """
        from .errors import check_llrp_response, LLRPError
        
        try:
            msg = DeleteAccessSpec(
                msg_id=self.connection.next_message_id,
                access_spec_id=access_spec_id
            )
            
            response = self.connection.send_recv(msg, timeout=5.0)
            
            if response and hasattr(response, 'llrp_status'):
                if response.llrp_status:
                    check_llrp_response(
                        response.llrp_status.status_code,
                        response.llrp_status.error_description,
                        raise_on_error=True
                    )
                    if access_spec_id == 0:
                        logger.info("All AccessSpecs deleted")
                    else:
                        logger.info(f"AccessSpec {access_spec_id} deleted")
                    return True
                return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
            
        except LLRPError as e:
            logger.error(f"LLRP error deleting AccessSpec: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
        except Exception as e:
            logger.error(f"Unexpected error deleting AccessSpec: {e}")
            return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def get_access_specs(self) -> Optional[List]:
        """
        Get all AccessSpecs from reader
        
        Returns:
            List of AccessSpec information or None if failed
        """
        from .errors import check_llrp_response, LLRPError
        
        try:
            msg = GetAccessSpecs(msg_id=self.connection.next_message_id)
            
            response = self.connection.send_recv(msg, timeout=10.0)
            
            if response and hasattr(response, 'llrp_status'):
                if response.llrp_status:
                    check_llrp_response(
                        response.llrp_status.status_code,
                        response.llrp_status.error_description,
                        raise_on_error=True
                    )
                    
                    access_specs_info = []
                    for access_spec in response.access_specs:
                        spec_info = {
                            'access_spec_id': access_spec.access_spec_id,
                            'antenna_id': access_spec.antenna_id,
                            'protocol_id': access_spec.protocol_id,
                            'current_state': access_spec.current_state,
                            'rospec_id': access_spec.rospec_id,
                            'operations': []
                        }
                        
                        # Parse operations
                        if access_spec.access_command:
                            for op_spec in access_spec.access_command.access_command_op_specs:
                                if hasattr(op_spec, 'memory_bank'):  # Read operation
                                    spec_info['operations'].append({
                                        'type': 'read',
                                        'op_spec_id': op_spec.op_spec_id,
                                        'memory_bank': op_spec.memory_bank,
                                        'word_pointer': op_spec.word_pointer,
                                        'word_count': getattr(op_spec, 'word_count', 0)
                                    })
                                elif hasattr(op_spec, 'write_data'):  # Write operation
                                    spec_info['operations'].append({
                                        'type': 'write',
                                        'op_spec_id': op_spec.op_spec_id,
                                        'memory_bank': op_spec.memory_bank,
                                        'word_pointer': op_spec.word_pointer,
                                        'write_data_length': len(op_spec.write_data)
                                    })
                        
                        access_specs_info.append(spec_info)
                    
                    return access_specs_info
                return None
            return None
            
        except LLRPError as e:
            logger.error(f"LLRP error getting AccessSpecs: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting AccessSpecs: {e}")
            return None
    
    def read_tag_memory(self, rospec_id: int, memory_bank: int = 1,
                       word_pointer: int = 2, word_count: int = 0,
                       access_password: int = 0, antenna_id: int = 0) -> bool:
        """
        Convenient method to read tag memory
        
        Args:
            rospec_id: ROSpec to bind the AccessSpec to
            memory_bank: Memory bank (0=Reserved, 1=EPC, 2=TID, 3=User)
            word_pointer: Starting word address
            word_count: Number of words to read (0 = read to end)
            access_password: Access password if needed
            antenna_id: Antenna ID (0 = all antennas)
            
        Returns:
            True if AccessSpec was set up successfully
        """
        access_spec_id = 1000  # Use fixed ID for convenience
        
        # Delete any existing AccessSpecs
        self.delete_access_spec(0)
        
        # Create read AccessSpec
        access_spec = self.create_read_access_spec(
            access_spec_id=access_spec_id,
            rospec_id=rospec_id,
            antenna_id=antenna_id,
            memory_bank=memory_bank,
            word_pointer=word_pointer,
            word_count=word_count,
            access_password=access_password
        )
        
        # Add and enable AccessSpec
        if self.add_access_spec(access_spec):
            return self.enable_access_spec(access_spec_id)
        
        return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def write_tag_memory(self, rospec_id: int, write_data: bytes,
                        memory_bank: int = 3, word_pointer: int = 0,
                        access_password: int = 0, antenna_id: int = 0) -> bool:
        """
        Convenient method to write tag memory
        
        Args:
            rospec_id: ROSpec to bind the AccessSpec to
            write_data: Data to write (word-aligned)
            memory_bank: Memory bank (usually 3=User)
            word_pointer: Starting word address
            access_password: Access password if needed
            antenna_id: Antenna ID (0 = all antennas)
            
        Returns:
            True if AccessSpec was set up successfully
        """
        access_spec_id = 1001  # Use fixed ID for convenience
        
        # Delete any existing AccessSpecs
        self.delete_access_spec(0)
        
        # Create write AccessSpec
        access_spec = self.create_write_access_spec(
            access_spec_id=access_spec_id,
            rospec_id=rospec_id,
            antenna_id=antenna_id,
            memory_bank=memory_bank,
            word_pointer=word_pointer,
            write_data=write_data,
            access_password=access_password
        )
        
        # Add and enable AccessSpec
        if self.add_access_spec(access_spec):
            return self.enable_access_spec(access_spec_id)
        
        return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    # Advanced ROSpec Methods
    
    def create_periodic_rospec(self, rospec_id: int = None,
                              period_seconds: float = 60.0,
                              offset_seconds: float = 0.0,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              report_every_n_tags: int = 1) -> ROSpec:
        """
        Create a ROSpec with periodic triggering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            period_seconds: Period between inventories in seconds
            offset_seconds: Initial delay before first inventory
            duration_seconds: Duration of each inventory
            antenna_ids: List of antenna IDs (None = all)
            report_every_n_tags: Report frequency
            
        Returns:
            Configured ROSpec with periodic trigger
        """
        from .advanced_rospec_parameters import (
            EnhancedROSpecStartTrigger, EnhancedROSpecStopTrigger,
            PeriodicTriggerValue
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=report_every_n_tags,
            start_immediate=False
        )
        
        # Create periodic start trigger
        periodic_trigger = PeriodicTriggerValue(
            offset=int(offset_seconds * 1000),
            period=int(period_seconds * 1000)
        )
        
        start_trigger = EnhancedROSpecStartTrigger(trigger_type=2)  # Periodic
        start_trigger.periodic_trigger_value = periodic_trigger
        
        rospec.ro_boundary_spec.rospec_start_trigger = start_trigger
        
        logger.info(f"Created periodic ROSpec {rospec_id}: every {period_seconds}s for {duration_seconds}s")
        return rospec
    
    def create_gpi_triggered_rospec(self, rospec_id: int = None,
                                   gpi_port: int = 1,
                                   gpi_event: bool = True,
                                   duration_seconds: float = 5.0,
                                   antenna_ids: List[int] = None,
                                   stop_on_gpi: bool = False,
                                   stop_gpi_port: int = 1,
                                   stop_gpi_event: bool = False) -> ROSpec:
        """
        Create a ROSpec triggered by GPI (GPIO input)
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            gpi_port: GPI port number for start trigger
            gpi_event: GPI event for start (True=High, False=Low)
            duration_seconds: Maximum duration of inventory
            antenna_ids: List of antenna IDs (None = all)
            stop_on_gpi: Whether to stop on GPI event
            stop_gpi_port: GPI port for stop trigger
            stop_gpi_event: GPI event for stop
            
        Returns:
            Configured ROSpec with GPI triggers
        """
        from .advanced_rospec_parameters import (
            EnhancedROSpecStartTrigger, EnhancedROSpecStopTrigger,
            GPITriggerValue, GPITriggerValueStop
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000) if not stop_on_gpi else 0,
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=False
        )
        
        # Create GPI start trigger
        gpi_start_trigger = GPITriggerValue(
            gpi_port_num=gpi_port,
            gpi_event=gpi_event,
            timeout=0
        )
        
        start_trigger = EnhancedROSpecStartTrigger(trigger_type=3)  # GPI
        start_trigger.gpi_trigger_value = gpi_start_trigger
        
        rospec.ro_boundary_spec.rospec_start_trigger = start_trigger
        
        # Create GPI stop trigger if requested
        if stop_on_gpi:
            gpi_stop_trigger = GPITriggerValueStop(
                gpi_port_num=stop_gpi_port,
                gpi_event=stop_gpi_event,
                timeout=int(duration_seconds * 1000) if duration_seconds > 0 else 0
            )
            
            stop_trigger = EnhancedROSpecStopTrigger(trigger_type=2)  # GPI
            stop_trigger.gpi_trigger_value = gpi_stop_trigger
            
            rospec.ro_boundary_spec.rospec_stop_trigger = stop_trigger
        
        logger.info(f"Created GPI-triggered ROSpec {rospec_id}: port {gpi_port}, event {'High' if gpi_event else 'Low'}")
        return rospec
    
    def start_periodic_inventory(self, period_seconds: float = 60.0,
                               duration_seconds: float = 5.0,
                               offset_seconds: float = 0.0,
                               antenna_ids: List[int] = None,
                               tag_callback: Callable = None) -> bool:
        """
        Start periodic inventory with automatic ROSpec management
        
        Args:
            period_seconds: Period between inventories
            duration_seconds: Duration of each inventory
            offset_seconds: Initial delay
            antenna_ids: List of antenna IDs
            tag_callback: Function called for each tag
            
        Returns:
            True if started successfully
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create periodic ROSpec
        rospec = self.create_periodic_rospec(
            rospec_id=789,
            period_seconds=period_seconds,
            offset_seconds=offset_seconds,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            report_every_n_tags=1
        )
        
        # Add and enable ROSpec
        if self.add_rospec(rospec):
            if self.enable_rospec(789):
                logger.info(f"Started periodic inventory: every {period_seconds}s for {duration_seconds}s")
                return True
        
        return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts
    
    def start_gpi_triggered_inventory(self, gpi_port: int = 1,
                                    gpi_event: bool = True,
                                    duration_seconds: float = 5.0,
                                    antenna_ids: List[int] = None,
                                    tag_callback: Callable = None) -> bool:
        """
        Start GPI-triggered inventory
        
        Args:
            gpi_port: GPI port number
            gpi_event: GPI event to trigger on (True=High, False=Low)
            duration_seconds: Maximum inventory duration
            antenna_ids: List of antenna IDs
            tag_callback: Function called for each tag
            
        Returns:
            True if started successfully
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create GPI-triggered ROSpec
        rospec = self.create_gpi_triggered_rospec(
            rospec_id=790,
            gpi_port=gpi_port,
            gpi_event=gpi_event,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Add and enable ROSpec
        if self.add_rospec(rospec):
            if self.enable_rospec(790):
                logger.info(f"Started GPI-triggered inventory: port {gpi_port}, {'rising' if gpi_event else 'falling'} edge")
                return True
        
        return False
    
    # EPC Gen2 Advanced Methods
    
    def create_filtered_rospec(self, rospec_id: int = None,
                              epc_filter: str = "",
                              memory_bank: int = 1,
                              duration_seconds: float = 5.0,
                              antenna_ids: List[int] = None,
                              state_aware: bool = False,
                              session: int = 0) -> ROSpec:
        """
        Create a ROSpec with EPC Gen2 filtering
        
        Args:
            rospec_id: ROSpec ID (auto-assigned if None)
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter (1=EPC, 2=TID, 3=User)
            duration_seconds: Inventory duration
            antenna_ids: List of antenna IDs
            state_aware: Use state-aware inventory
            session: Gen2 session number (0-3)
            
        Returns:
            ROSpec with C1G2 filtering
        """
        from .c1g2_parameters import (
            C1G2InventoryCommand, C1G2Filter, C1G2SingulationControl,
            C1G2TagInventoryStateAware
        )
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command
        c1g2_inventory = C1G2InventoryCommand()
        c1g2_inventory.tag_inventory_state_aware = state_aware
        
        # Add EPC filter if specified
        if epc_filter:
            # Convert hex string to bytes
            try:
                filter_data = bytes.fromhex(epc_filter.replace(' ', ''))
                bit_length = len(filter_data) * 8
                
                epc_filter_param = C1G2Filter(
                    filter_type=3,  # Memory_Bank_Filter
                    memory_bank=memory_bank,
                    bit_pointer=32 if memory_bank == 1 else 0,  # Skip PC+CRC for EPC
                    bit_length=bit_length,
                    filter_data=filter_data
                )
                c1g2_inventory.c1g2_filter.append(epc_filter_param)
                
            except ValueError:
                logger.warning(f"Invalid hex EPC filter: {epc_filter}")
        
        # Add singulation control
        singulation_control = C1G2SingulationControl(
            session=session,
            tag_population=32,
            tag_transit_time=0
        )
        
        if state_aware:
            state_aware_param = C1G2TagInventoryStateAware(
                tag_state=0,  # State A
                session=session
            )
            singulation_control.c1g2_tag_inventory_state_aware = state_aware_param
        
        c1g2_inventory.c1g2_singulation_control = singulation_control
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created filtered ROSpec {rospec_id}: filter='{epc_filter}', bank={memory_bank}")
        return rospec
    
    def create_selective_rospec(self, rospec_id: int = None,
                               target_tags: List[Dict] = None,
                               duration_seconds: float = 5.0,
                               antenna_ids: List[int] = None) -> ROSpec:
        """
        Create ROSpec that selectively targets specific tags
        
        Args:
            rospec_id: ROSpec ID
            target_tags: List of target tag specifications
                        [{'epc': 'hex_string', 'memory_bank': 1, 'match': True}, ...]
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            
        Returns:
            ROSpec with selective targeting
        """
        from .c1g2_parameters import C1G2InventoryCommand, C1G2TagSpec, C1G2TargetTag
        
        if rospec_id is None:
            rospec_id = self.current_rospec_id
            self.current_rospec_id += 1
        
        # Create basic ROSpec
        rospec = self.create_basic_rospec(
            rospec_id=rospec_id,
            duration_ms=int(duration_seconds * 1000),
            antenna_ids=antenna_ids,
            report_every_n_tags=1,
            start_immediate=True
        )
        
        # Create C1G2 inventory command with tag targeting
        c1g2_inventory = C1G2InventoryCommand()
        
        if target_tags:
            for tag_spec in target_tags:
                epc_hex = tag_spec.get('epc', '')
                memory_bank = tag_spec.get('memory_bank', 1)
                match = tag_spec.get('match', True)
                
                if epc_hex:
                    try:
                        tag_data = bytes.fromhex(epc_hex.replace(' ', ''))
                        
                        # Create target tag
                        target_tag = C1G2TargetTag(
                            memory_bank=memory_bank,
                            match=match,
                            bit_pointer=32 if memory_bank == 1 else 0,
                            tag_mask=b'\xff' * len(tag_data),  # Full match mask
                            tag_data=tag_data
                        )
                        
                        # Create tag spec
                        tag_spec_param = C1G2TagSpec(target=4)  # SL (Selected)
                        tag_spec_param.c1g2_target_tag.append(target_tag)
                        
                        # Add as custom parameter (simplified implementation)
                        c1g2_inventory.custom_parameters.append(tag_spec_param)
                        
                    except ValueError:
                        logger.warning(f"Invalid hex EPC: {epc_hex}")
        
        # Add to AISpec
        if rospec.spec_parameters:
            aispec = rospec.spec_parameters[0]
            if aispec.inventory_parameter_specs:
                inv_param = aispec.inventory_parameter_specs[0]
                inv_param.antenna_configuration = c1g2_inventory
        
        logger.info(f"Created selective ROSpec {rospec_id}: {len(target_tags or [])} target tags")
        return rospec
    
    def start_filtered_inventory(self, epc_filter: str = "",
                                memory_bank: int = 1,
                                duration_seconds: float = 5.0,
                                antenna_ids: List[int] = None,
                                tag_callback: Callable = None,
                                state_aware: bool = False) -> List[Dict]:
        """
        Start inventory with EPC Gen2 filtering
        
        Args:
            epc_filter: EPC pattern to filter (hex string)
            memory_bank: Memory bank for filter
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            state_aware: Use state-aware inventory
            
        Returns:
            List of filtered tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create filtered ROSpec
        rospec = self.create_filtered_rospec(
            rospec_id=791,
            epc_filter=epc_filter,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids,
            state_aware=state_aware
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(791):
                logger.info(f"Started filtered inventory: filter='{epc_filter}'")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(791)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def start_selective_inventory(self, target_tags: List[Dict],
                                 duration_seconds: float = 5.0,
                                 antenna_ids: List[int] = None,
                                 tag_callback: Callable = None) -> List[Dict]:
        """
        Start inventory targeting specific tags
        
        Args:
            target_tags: List of target tag specifications
            duration_seconds: Inventory duration
            antenna_ids: Antenna IDs
            tag_callback: Tag callback function
            
        Returns:
            List of targeted tags
        """
        # Set callback
        if tag_callback:
            self.tag_callback = tag_callback
        
        # Clear existing ROSpecs
        self.clear_rospecs()
        
        # Create selective ROSpec
        rospec = self.create_selective_rospec(
            rospec_id=792,
            target_tags=target_tags,
            duration_seconds=duration_seconds,
            antenna_ids=antenna_ids
        )
        
        # Execute inventory
        if self.add_rospec(rospec):
            if self.enable_rospec(792):
                logger.info(f"Started selective inventory: {len(target_tags)} targets")
                
                # Wait for completion
                time.sleep(duration_seconds + 0.5)
                
                # Stop and clean up
                self.stop_rospec(792)
                self.clear_rospecs()
                
                # Return collected tags
                with self.tags_lock:
                    return self.tags_read.copy()
        
        return []
    
    def configure_gen2_settings(self, session: int = 0, 
                               tag_population: int = 32,
                               mode_index: int = 0,
                               tari: int = 0) -> bool:
        """
        Configure EPC Gen2 protocol settings
        
        Args:
            session: Gen2 session number (0-3)
            tag_population: Expected tag population
            mode_index: RF mode index from reader capabilities
            tari: Tari value in nanoseconds
            
        Returns:
            True if configured successfully
        """
        # Store settings for future ROSpec creation
        self._gen2_session = session
        self._gen2_tag_population = tag_population  
        self._gen2_mode_index = mode_index
        self._gen2_tari = tari
        
        logger.info(f"Gen2 settings: session={session}, population={tag_population}, mode={mode_index}")
        return True
    
    def find_tags_with_epc_pattern(self, epc_pattern: str,
                                  memory_bank: int = 1,
                                  duration_seconds: float = 10.0) -> List[Dict]:
        """
        Find tags matching EPC pattern
        
        Args:
            epc_pattern: Partial EPC pattern (hex string)
            memory_bank: Memory bank to search
            duration_seconds: Search duration
            
        Returns:
            List of matching tags
        """
        return self.start_filtered_inventory(
            epc_filter=epc_pattern,
            memory_bank=memory_bank,
            duration_seconds=duration_seconds
        )
    
    def count_tags_by_tid_manufacturer(self, duration_seconds: float = 5.0) -> Dict[str, int]:
        """
        Count tags by TID manufacturer
        
        Args:
            duration_seconds: Inventory duration
            
        Returns:
            Dictionary mapping manufacturer to count
        """
        # Get all tags with TID reading
        tags = self.start_filtered_inventory(
            epc_filter="",  # No filter
            memory_bank=2,  # TID memory
            duration_seconds=duration_seconds
        )
        
        manufacturer_counts = {}
        
        for tag in tags:
            # Extract manufacturer from TID (simplified)
            tid_hex = tag.get('tid', '')
            if len(tid_hex) >= 4:
                # First 2 bytes typically contain manufacturer info
                manufacturer = tid_hex[:4]
                manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
        
        return manufacturer_counts