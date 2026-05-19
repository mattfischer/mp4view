import stream
import syntax

from . import cabac

import math

class AVCBitstream(stream.Bitstream):
    def __init__(self, bytes, byte_start):
        super(AVCBitstream, self).__init__(bytes, byte_start)

    def getbytes(self, start, end):
        return self.bytes[start:end]

    def get_exp_golomb(self):
        leading_zero_bits = 0
        while True:
            b = self.getbit()
            if b:
                break
            else:
                leading_zero_bits += 1

        val = (1 << leading_zero_bits) - 1 + self.getbits(leading_zero_bits)
        return val

    def get_ue(self, name=None, format=None):
        if name:
            self.start_syntax_item()

        val = self.get_exp_golomb()

        title = None
        if name:
            if format:
                title = '%s: %s' % (name, format(val))
            else:
                title = '%s: %i' % (name, val)
            self.finish_syntax_item(title)
        return val

    def get_se(self, name=None, format=None):
        return self.get_ue(name, format)

class ParseObject:
    pass

enum_nal_unit_type = syntax.format_enum({
    0: 'Unspecified',
    1: 'Coded slice',
    2: 'Coded slice data partition A',
    3: 'Coded slice data partition B',
    4: 'Coded slice data partition C',
    5: 'Coded slice of an IDR picture',
    6: 'Supplemental enhancement information (SEI)',
    7: 'Sequence parameter set',
    8: 'Picture parameter set',
    9: 'Picture delimiter',
    10: 'End of sequence',
    11: 'End of stream',
    12: 'Filler data'
})

enum_slice_type = syntax.format_enum({
    0: 'P (P slice)',
    1: 'B (B slice)',
    2: 'I (I slice)',
    3: 'SP (SP slice)',
    4: 'SI (SI slice)',
    5: 'P (P slice)',
    6: 'B (B slice)',
    7: 'I (I slice)',
    8: 'SP (SP slice)',
    9: 'SI (SI slice)'
})

class NAL:
    def parse(self, bytes, byte_start, length, avc_configuration):
        self.bitstream = AVCBitstream(bytes, byte_start)

        self.bitstream.start_syntax_item('NAL')
        forbidden_zero_bit = self.bitstream.getbits(1)
        self.nal_ref_idc = self.bitstream.getbits(2, 'nal_ref_idc')
        self.nal_unit_type = self.bitstream.getbits(5, 'nal_unit_type', format=enum_nal_unit_type)

        self.parse_nal(avc_configuration)
        
        self.syntax_item = self.bitstream.finish_syntax_item()

    def parse_nal(self, avc_configuration):
        if self.nal_unit_type == 1:
            self.slice_layer = self.parse_slice_layer_without_partitioning(avc_configuration)
        elif self.nal_unit_type == 5:
            self.slice_layer = self.parse_slice_layer_without_partitioning(avc_configuration)
        elif self.nal_unit_type == 7:
            self.seq_parameter_set = self.parse_seq_parameter_set()
        elif self.nal_unit_type == 8:
            self.pic_parameter_set = self.parse_pic_parameter_set()

    def parse_seq_parameter_set(self):
        self.bitstream.start_syntax_item('seq_parameter_set')
        sps = ParseObject()
        sps.profile_idc = self.bitstream.getbits(8, 'profile_idc')
        sps.constraint_set0_flag = self.bitstream.getbits(1, 'constraint_set0_flag')
        sps.constraint_set1_flag = self.bitstream.getbits(1, 'constraint_set1_flag')
        sps.constraint_set2_flag = self.bitstream.getbits(1, 'constraint_set2_flag')
        sps.constraint_set3_flag = self.bitstream.getbits(1, 'constraint_set3_flag')
        sps.constraint_set4_flag = self.bitstream.getbits(1, 'constraint_set4_flag')
        sps.constraint_set5_flag = self.bitstream.getbits(1, 'constraint_set5_flag')
        reserved_zero_2bits = self.bitstream.getbits(2)
        sps.level_idc = self.bitstream.getbits(8, 'level_idc')
        sps.seq_parameter_set_id = self.bitstream.get_ue('seq_parameter_set_id')
        sps.separate_colour_plane_flag = 0
        if sps.profile_idc in (100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135):
            sps.chroma_format_idc = self.bitstream.get_ue('chroma_format_idc')
            if sps.chroma_format_idc == 3:
                sps.separate_colour_plane_flag = self.bitstream.getbits(1, 'separate_colour_plane_flag')
            sps.bit_depth_luma_minus8 = self.bitstream.get_ue('bit_depth_luma_minus8')
            sps.bit_depth_chroma_minus8 = self.bitstream.get_ue('bit_depth_chroma_minus8')
            sps.qpprime_y_zero_transform_bypass_flag = self.bitstream.getbits(1, 'qpprime_y_zero_transform_bypass_flag')
            sps.seq_scaling_matrix_present_flag = self.bitstream.getbits(1, 'seq_scaling_matrix_present_flag')
            if sps.seq_scaling_matrix_present_flag:
                count = 8 if sps.chroma_format_idc != 3 else 12
                sps.seq_scaling_list_present_flag = [0] * count
                for i in range(count):
                    sps.seq_scaling_list_present_flag[i] = self.bitstream.getbits(1, 'seq_scaling_list_present_flag')
                
        sps.log2_max_frame_num_minus4 = self.bitstream.get_ue('log2_max_frame_num_minus4')
        sps.pic_order_cnt_type = self.bitstream.get_ue('pic_order_cnt_type')
        if sps.pic_order_cnt_type == 0:
            sps.log2_max_pic_order_cnt_lsb_minus4 = self.bitstream.get_ue('log2_max_pic_order_cnt_lsb_minus4')
        elif sps.pic_order_cnt_type == 1:
            sps.delta_pic_order_always_zero_flag = self.bitstream.getbits(1, 'delta_pic_order_always_zero_flag')
            sps.offset_for_non_ref_pic = self.bitstream.get_se('offset_for_non_ref_pic')
            sps.offset_for_top_to_bottom_field = self.bitstream.get_se('offset_for_top_to_bottom_field')
            sps.num_ref_frames_in_pic_order_cnt_cycle = self.bitstream.get_ue('num_ref_frames_in_pic_order_cnt_cycle')
            sps.offset_for_ref_frame = [0] * sps.num_ref_frames_in_pic_order_cnt_cycle
            self.bitstream.start_syntax_item('offset_for_ref_frame')
            for i in range(sps.num_ref_frames_in_pic_order_cnt_cycle):
                sps.offset_for_ref_frame[i] = self.bitstream.get_se('%i' % i)
            self.bitstream.finish_syntax_item()
        sps.num_ref_frames = self.bitstream.get_ue('num_ref_frames')
        sps.gaps_in_frame_num_value_allowed_flag = self.bitstream.getbits(1, 'gaps_in_frame_num_value_allowed_flag')
        sps.pic_width_in_mbs_minus1 = self.bitstream.get_ue('pic_width_in_mbs_minus1')
        sps.pic_height_in_map_units_minus1 = self.bitstream.get_ue('pic_height_in_map_units_minus1')
        sps.frame_mbs_only_flag = self.bitstream.getbits(1, 'frame_mbs_only_flag')
        if not sps.frame_mbs_only_flag:
            sps.mb_adaptive_frame_field_flag = self.bitstream.getbits(1, 'mb_adaptive_frame_field_flag')
        sps.direct_8x8_inference_flag = self.bitstream.getbits(1, 'direct_8x8_inference_flag')
        sps.frame_cropping_flag = self.bitstream.getbits(1, 'frame_cropping_flag')
        if sps.frame_cropping_flag:
            sps.frame_crop_left_offset = self.bitstream.get_ue('frame_crop_left_offset')
            sps.frame_crop_right_offset = self.bitstream.get_ue('frame_crop_right_offset')
            sps.frame_crop_top_offset = self.bitstream.get_ue('frame_crop_top_offset')
            sps.frame_crop_bottom_offset = self.bitstream.get_ue('frame_crop_bottom_offset')

        sps.vui_parameters_present_flag = self.bitstream.getbits(1, 'vui_parameters_present_flag')
        #if sps.vui_parameters_present_flag:
        #    sps.vui_parameters = self.parse_vui_parameters()
        
        self.bitstream.finish_syntax_item()
        return sps

    def parse_pic_parameter_set(self):
        self.bitstream.start_syntax_item('pic_parameter_set')
        pps = ParseObject()
        pps.pic_parameter_set_id = self.bitstream.get_ue('pic_parameter_set_id')
        pps.seq_parameter_set_id = self.bitstream.get_ue('seq_parameter_set_id')
        pps.entropy_coding_mode_flag = self.bitstream.getbits(1, 'entropy_coding_mode_flag')
        pps.bottom_field_pic_order_in_frame_present_flag = self.bitstream.getbits(1, 'bottom_field_pic_order_in_frame_present_flag')
        pps.num_slice_groups_minus1 = self.bitstream.get_ue('num_slice_groups_minus1')
        
        if pps.num_slice_groups_minus1 > 0:
            pps.slice_group_map_type = self.bitstream.get_ue('slice_group_map_type')
            if pps.slice_group_map_type == 0:
                pps.run_length_minus1 = [0] * (pps.num_slice_groups_minus1 + 1)
                self.bitstream.start_syntax_item('run_length_minus1')
                for iGroup in range(pps.num_slice_groups_minus1 + 1):
                    pps.run_length_minus1[iGroup] = self.bitstream.get_ue('%i' % iGroup)
                self.bitstream.finish_syntax_item()
            elif pps.slice_group_map_type == 2:
                pps.top_left = [0] * pps.num_slice_groups_minus1
                pps.bottom_right = [0] * pps.num_slice_groups_minus1
                self.bitstream.start_syntax_item('group')
                for iGroup in range(pps.num_slice_groups_minus1):
                    pps.top_left[iGroup] = self.bitstream.get_ue('top_left %i' % iGroup)
                    pps.bottom_right[iGroup] = self.bitstream.get_ue('bottom_right %i' % iGroup)
                self.bitstream.finish_syntax_item()
            elif pps.slice_group_map_type in (3, 4, 5):
                pps.slice_group_change_direction_flag = self.bitstream.getbits(1, 'slice_group_change_direction_flag')
                pps.slice_group_change_rate_minus1 = self.bitstream.get_ue('slice_group_change_rate_minus1')
            elif pps.slice_group_map_type == 6:
                pps.pic_size_in_map_units_minus1 = self.bitstream.get_ue('pic_size_in_map_units_minus1')
                pps.slice_group_id = [0] * (pps.pic_size_in_map_units_minus1 + 1)
                self.bitstream.start_syntax_item('slice_group_id')
                for i in range(pps.pic_size_in_map_units_minus1 + 1):
                    pps.slice_group_id[i] = self.bitstream.getbits(1, '%i' % i)
                self.bitstream.finish_syntax_item()

        pps.num_ref_idx_l0_active_minus1 = self.bitstream.get_ue('num_ref_idx_l0_active_minus1')
        pps.num_ref_idx_l1_active_minus1 = self.bitstream.get_ue('num_ref_idx_l1_active_minus1')
        pps.weighted_pred_flag = self.bitstream.getbits(1, 'weighted_pred_flag')
        pps.weighted_bipred_idc = self.bitstream.getbits(2, 'weighted_bipred_idc')
        pps.pic_init_qp_minus26 = self.bitstream.get_se('pic_init_qp_minus26')
        pps.pic_init_qs_minus26 = self.bitstream.get_se('pic_init_qs_minus26')
        pps.chroma_qp_index_offset = self.bitstream.get_se('chroma_qp_index_offset')
        pps.deblocking_filter_control_present_flag = self.bitstream.getbits(1, 'deblocking_filter_control_present_flag')
        pps.constrained_intra_pred_flag = self.bitstream.getbits(1, 'constrained_intra_pred_flag')    
        pps.redundant_pic_cnt_present_flag = self.bitstream.getbits(1, 'redundant_pic_cnt_present_flag')

        self.bitstream.finish_syntax_item()
        return pps

    def parse_slice_layer_without_partitioning(self, avc_configuration):
        self.bitstream.start_syntax_item('slice_layer_without_partitioning')
        slice_layer = ParseObject()
        (slice_layer.slice_header, sps, pps) = self.parse_slice_header(avc_configuration)
        slice_layer.slice_data = self.parse_slice_data(slice_layer.slice_header, sps, pps)
        self.bitstream.finish_syntax_item()
        return slice_layer

    def parse_slice_header(self, avc_configuration):
        self.bitstream.start_syntax_item('slice_header')
        slice_header = ParseObject()
        
        slice_header.first_mb_in_slice = self.bitstream.get_ue('first_mb_in_slice')
        slice_header.slice_type = self.bitstream.get_ue('slice_type', format=enum_slice_type)
        slice_header.pic_parameter_set_id = self.bitstream.get_ue('pic_parameter_set_id')
        pps = None
        for p in avc_configuration.avcConfig.pps_nals:
            if p.pic_parameter_set.pic_parameter_set_id == slice_header.pic_parameter_set_id:
                pps = p.pic_parameter_set
                break
        sps = None
        for s in avc_configuration.avcConfig.sps_nals:
            if s.seq_parameter_set.seq_parameter_set_id == pps.seq_parameter_set_id:
                sps = s.seq_parameter_set
                break

        if sps.separate_colour_plane_flag == 1:
            slice_header.colour_plane_id = self.bitstream.getbits(2, 'colour_plane_id')
        slice_header.frame_num = self.bitstream.getbits(sps.log2_max_frame_num_minus4 + 4, 'frame_num')
        if not sps.frame_mbs_only_flag:
            slice_header.field_pic_flag = self.bitstream.getbits(1, 'field_pic_flag')
            if slice_header.field_pic_flag:
                slice_header.bottom_field_flag = self.bitstream.getbits(1, 'bottom_field_flag')
    
        IdrPicFlag = (self.nal_unit_type == 5)
        if IdrPicFlag:
            slice_header.idr_pic_id = self.bitstream.get_ue('idr_pic_id')

        if sps.pic_order_cnt_type == 0:
            slice_header.pic_order_cnt_lsb = self.bitstream.getbits(sps.log2_max_pic_order_cnt_lsb_minus4 + 4, 'pic_order_cnt_lsb')
            if pps.bottom_field_pic_order_in_frame_present_flag and not slice_header.field_pic_flag:
                slice_header.delta_pic_order_cnt_bottom = self.bitstream.get_se('delta_pic_order_cnt_bottom')

        slice_header.delta_pic_order_cnt = [0] * 2
        if sps.pic_order_cnt_type == 1 and not sps.pic_order_cnt_type:
            slice_header.delta_pic_order_cnt[0] = self.bitstream.get_se('delta_pic_order_cnt[0]')
            if pps.bottom_field_pic_order_in_frame_present_flag and not slice_header.field_pic_flag:
                slice_header.delta_pic_order_cnt[1] = self.bitstream.get_se('delta_pic_order_cnt[1]')

        if pps.redundant_pic_cnt_present_flag:
            slice_header.redundant_pic_cnt = self.bitstream.get_ue('redundant_pic_cnt')

        if slice_header.slice_type in (1, 6):
            slice_header.direct_spatial_mv_pred_flag = self.bitstream.getbits(1, 'direct_spatial_mv_pred_flag')

        if slice_header.slice_type in (0, 1, 3, 5, 6, 9):
            slice_header.num_ref_idx_active_override_flag = self.bitstream.getbits(1, 'num_ref_idx_active_override_flag')
            if slice_header.num_ref_idx_active_override_flag:
                slice_header.num_ref_idx_l0_active_minus1 = self.bitstream.get_ue('num_ref_idx_l0_active_minus1')
                if slice_header.slice_type in (1, 6):
                    slice_header.num_ref_idx_l1_active_minus1 = self.bitstream.get_ue('num_ref_idx_l1_active_minus1')

        slice_header.ref_pic_list_modification = self.parse_ref_pic_list_modification(slice_header.slice_type)
        if (pps.weighted_pred_flag and slice_header.slice_type in (0, 3)) or (pps.weighted_bipred_idc and slice_header.slice_type == 1):
            slice_header.pred_weight_table = self.parse_pred_weight_table(slice_header.slice_type, sps, pps)
        
        if self.nal_ref_idc != 0:
            slice_header.dec_ref_pic_marking = self.parse_dec_ref_pic_marking()

        if pps.entropy_coding_mode_flag and slice_header.slice_type not in (2, 4, 7, 9):   
            slice_header.cabac_init_idc = self.bitstream.get_ue('cabac_init_idc')
        slice_header.slice_qp_delta = self.bitstream.get_se('slice_qp_delta')

        if slice_header.slice_type in (3, 4, 8, 9):
            if slice_header.slice_type == 3:
                slice_header.sp_for_switch_flag = self.bitstream.getbits(1, 'sp_for_switch_flag')
            slice_header.slice_qs_delta = self.bitstream.get_se('slice_qs_delta')

        if pps.deblocking_filter_control_present_flag:
            slice_header.disable_deblocking_filter_idc = self.bitstream.get_ue('disable_deblocking_filter_idc')
            if slice_header.disable_deblocking_filter_idc != 1:
                slice_header.slice_alpha_c0_offset_div2 = self.bitstream.get_se('slice_alpha_c0_offset_div2')
                slice_header.slice_beta_offset_div2 = self.bitstream.get_se('slice_beta_offset_div2')

        if pps.num_slice_groups_minus1 > 0 and pps.slice_group_map_type >= 3 and pps.slice_group_map_type <= 5:
            SliceGroupChangeRate = pps.slice_group_change_rate_minus1 + 1
            PicSizeInMapUnits = pps.pic_size_in_map_units_minus1 + 1
            count = math.ceil(math.log(PicSizeInMapUnits // SliceGroupChangeRate + 1, 2))
            slice_header.slice_group_change_cycle = self.bitstream.getbits(count, 'slice_group_change_cycle')

        self.bitstream.finish_syntax_item()
        return (slice_header, sps, pps)

    def parse_ref_pic_list_modification(self, slice_type):
        self.bitstream.start_syntax_item('ref_pic_list_modification')
        rplm = ParseObject()

        if slice_type % 5 != 2 and slice_type % 5 != 4:
            ref_pic_list_modification_flag_l0 = self.bitstream.getbits(1)
            if ref_pic_list_modification_flag_l0:
                while True:
                    modification_of_pic_nums_idc = self.bitstream.get_ue()
                    if modification_of_pic_nums_idc in (0, 1):
                        abs_diff_pic_num_minus1 = self.bitstream.get_ue('abs_diff_pic_num_minus1')
                    elif modification_of_pic_nums_idc == 2:
                        long_term_pic_num = self.bitstream.get_ue('long_term_pic_num')
                    elif modification_of_pic_nums_idc == 3:
                        break

        if slice_type % 5 == 1:
            ref_pic_list_modification_flag_l1 = self.bitstream.getbits(1)
            if ref_pic_list_modification_flag_l1:
                while True:
                    modification_of_pic_nums_idc = self.bitstream.get_ue()
                    if modification_of_pic_nums_idc in (0, 1):
                        abs_diff_pic_num_minus1 = self.bitstream.get_ue('abs_diff_pic_num_minus1 (B)')
                    elif modification_of_pic_nums_idc == 2:
                        long_term_pic_num = self.bitstream.get_ue('long_term_pic_num (B)')
                    elif modification_of_pic_nums_idc == 3:
                        break

        self.bitstream.finish_syntax_item()
        return rplm

    def parse_pred_weight_table(self, slice_type, sps, pps):
        self.bitstream.start_syntax_item('pred_weight_table')
        pwt = ParseObject()
        pwt.luma_log2_weight_denom = self.bitstream.get_ue('luma_log2_weight_denom')
        ChromaArrayType = sps.chroma_format_idc if sps.separate_colour_plane_flag == 1 else 0
        if ChromaArrayType != 0:
            pwt.chroma_log2_weight_denom = self.bitstream.get_ue('chroma_log2_weight_denom')

        pwt.luma_weight_l0 = [0] * pps.num_ref_idx_l0_active_minus1
        pwt.luma_offset_l0 = [0] * pps.num_ref_idx_l0_active_minus1
        pwt.chroma_weight_l0 = [None] * pps.num_ref_idx_l0_active_minus1
        pwt.chroma_offset_l0 = [None] * pps.num_ref_idx_l0_active_minus1
        for i in range(pps.num_ref_idx_l0_active_minus1):
            luma_weight_l0_flag = self.bitstream.getbits(1)
            if luma_weight_l0_flag:
                pwt.luma_weight_l0[i] = self.bitstream.get_se('luma_weight_l0[%i]' % i)
                pwt.luma_offset_l0[i] = self.bitstream.get_se('luma_offset_l0[%i]' % i)

            if ChromaArrayType != 0:
                chroma_weight_l0_flag = self.bitstream.getbits(1)
                if chroma_weight_l0_flag:
                    pwt.chroma_weight_l0[i] = [0] * 2
                    pwt.chroma_offset_l0[i] = [0] * 2
                    for j in range(2):
                        pwt.chroma_weight_l0[i][j] = self.bitstream.get_se('chroma_weight_l0[%i][%i]' % (i, j))
                        pwt.chroma_offset_l0[i][j] = self.bitstream.get_se('chroma_offset_l0[%i][%i]' % (i, j))

        if slice_type % 5 == 1:
            pwt.luma_weight_l1 = [0] * pps.num_ref_idx_l1_active_minus1
            pwt.luma_offset_l1 = [0] * pps.num_ref_idx_l1_active_minus1
            pwt.chroma_weight_l1 = [None] * pps.num_ref_idx_l1_active_minus1
            pwt.chroma_offset_l1 = [None] * pps.num_ref_idx_l1_active_minus1
            for i in range(pps.num_ref_idx_l1_active_minus1):
                luma_weight_l1_flag = self.bitstream.getbits(1)
                if luma_weight_l1_flag:
                    pwt.luma_weight_l1[i] = self.bitstream.get_se('luma_weight_l1[%i]' % i)
                    pwt.luma_offset_l1[i] = self.bitstream.get_se('luma_offset_l1[%i]' % i)

                if ChromaArrayType != 0:
                    chroma_weight_l1_flag = self.bitstream.getbits(1)
                    if chroma_weight_l1_flag:
                        pwt.chroma_weight_l1[i] = [0] * 2
                        pwt.chroma_offset_l1[i] = [0] * 2
                        for j in range(2):
                            pwt.chroma_weight_l1[i][j] = self.bitstream.get_se('chroma_weight_l1[%i][%i]' % (i, j))
                            pwt.chroma_offset_l1[i][j] = self.bitstream.get_se('chroma_offset_l1[%i][%i]' % (i, j))

        self.bitstream.finish_syntax_item()
        return pwt

    def parse_dec_ref_pic_marking(self):
        self.bitstream.start_syntax_item('dec_ref_pic_marking')
        drpm = ParseObject()

        IdrPicFlag = (self.nal_unit_type == 5)
        if IdrPicFlag:
            drpm.no_output_of_prior_pics_flag = self.bitstream.getbits(1, 'no_output_of_prior_pics_flag')
            drpm.long_term_reference_flag = self.bitstream.getbits(1, 'long_term_reference_flag')
        else:
            adaptive_ref_pic_marking_mode_flag = self.bitstream.getbits(1)
            if adaptive_ref_pic_marking_mode_flag:
                while True:
                    memory_management_control_operation = self.bitstream.get_ue('memory_management_control_operation')
                    if memory_management_control_operation in (1, 3):
                        difference_of_pic_nums_minus1 = self.bitstream.get_ue('difference_of_pic_nums_minus1')
                    elif memory_management_control_operation == 2:
                        long_term_pic_num = self.bitstream.get_ue('long_term_pic_num')
                    elif memory_management_control_operation in (3, 6):
                        long_term_frame_idx = self.bitstream.get_ue('long_term_frame_idx')
                    elif memory_management_control_operation == 4:
                        max_long_term_frame_idx_plus1 = self.bitstream.get_ue('max_long_term_frame_idx_plus1')
                    elif memory_management_control_operation == 0:
                        break

        self.bitstream.finish_syntax_item()
        return drpm

    def parse_slice_data(self, slice_header, sps, pps):
        if pps.entropy_coding_mode_flag == 1:
            return self.parse_slice_data_cabac(slice_header, sps, pps)
        else:
            return None
        

    def parse_slice_data_cabac(self, slice_header, sps, pps):
        self.bitstream.start_syntax_item('slice_data')
        slice_data = ParseObject()
        while self.bitstream.pos % 8 != 0:
            cabac_alignment_one_bit = self.bitstream.getbit()

        cabac_decoder = cabac.Decoder(self.bitstream, slice_header, sps, pps)

        self.bitstream.finish_syntax_item()
        return slice_data

class NALU:
    def parse(self, bytes, byte_start, avc_configuration):
        bitstream = stream.Bitstream(bytes, byte_start)
        bitstream.start_syntax_item('NALU')

        length_size = avc_configuration.avcConfig.lengthSizeMinusOne + 1

        total_length = 0
        self.nals = []
        while total_length < len(bytes):
            NALUnitLength = bitstream.getbits(8 * length_size)
            nal = NAL()
            total_length += length_size
            nal.parse(bytes[total_length:total_length + NALUnitLength], byte_start + total_length, NALUnitLength, avc_configuration)
            bitstream.append_syntax_item(nal.syntax_item)
            bitstream.pos += NALUnitLength * 8
            self.nals.append(nal)
            total_length += NALUnitLength
        self.syntax_item = bitstream.finish_syntax_item()