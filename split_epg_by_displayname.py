#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import requests
import os
import sys
import re
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="按电视台显示名称拆分 EPG XML 文件")
    parser.add_argument('--url', default="https://raw.githubusercontent.com/9602894/sandiJMYG/main/epg_data/epg_merged.xml",
                        help='EPG XML 文件的 URL')
    parser.add_argument('--output', default="epg_by_channel_displayname",
                        help='输出根目录名称')
    args = parser.parse_args()

    epg_url = args.url
    output_base_dir = args.output

    # 创建输出目录
    os.makedirs(output_base_dir, exist_ok=True)

    print(f"⏳ 正在从 {epg_url} 下载 EPG 文件...")

    try:
        response = requests.get(epg_url, timeout=60)
        response.raise_for_status()
        xml_content = response.text
        print("✅ EPG 文件下载成功！")
    except requests.exceptions.RequestException as e:
        print(f"❌ 下载 EPG 文件失败: {e}")
        sys.exit(1)

    try:
        root = ET.fromstring(xml_content)

        # 处理命名空间
        namespaces = {}
        for elem in root.iter():
            if '}' in elem.tag:
                uri = elem.tag.split('}')[0].strip('{')
                if uri not in namespaces.values():
                    prefix = f"ns{len(namespaces)}"
                    namespaces[prefix] = uri
                    ET.register_namespace(prefix, uri)
            break  # 只需查看根元素

        if namespaces:
            ns = {'xmltv': list(namespaces.values())[0]}
        else:
            ns = {}

        def find_elements(parent, tag, ns=ns):
            if ns:
                elements = parent.findall(f'.//xmltv:{tag}', ns)
                if elements:
                    return elements
            return parent.findall(f'.//{tag}')

        # 获取所有 channel
        channel_elements = find_elements(root, 'channel')
        if not channel_elements:
            channel_elements = [elem for elem in root.iter() if elem.tag.endswith('channel')]

        # 建立 channel id -> display-name 映射
        channel_name_map = {}
        for ch in channel_elements:
            ch_id = ch.get('id')
            if not ch_id:
                continue
            display_names = find_elements(ch, 'display-name')
            if display_names:
                display_name = display_names[0].text
                if display_name:
                    channel_name_map[ch_id] = display_name.strip()
                else:
                    channel_name_map[ch_id] = ch_id
            else:
                channel_name_map[ch_id] = ch_id

        print(f"✅ 找到 {len(channel_name_map)} 个频道定义")

        # 获取所有 programme
        programme_elements = find_elements(root, 'programme')
        if not programme_elements:
            programme_elements = [elem for elem in root.iter() if elem.tag.endswith('programme')]

        if not programme_elements:
            print("❌ 未找到任何 programme 条目")
            sys.exit(1)

        print(f"✅ 找到 {len(programme_elements)} 个节目条目")

        # 按 display-name 分组
        grouped = {}
        for prog in programme_elements:
            ch_id = prog.get('channel')
            if not ch_id:
                group_key = "unknown"
            else:
                group_key = channel_name_map.get(ch_id, ch_id)
            grouped.setdefault(group_key, []).append(prog)

        print(f"✅ 共分为 {len(grouped)} 个电视台组")

        # 准备 XML 头尾
        tv_attrib = root.attrib
        header = f'<?xml version="1.0" encoding="UTF-8"?>\n<tv'
        for key, value in tv_attrib.items():
            header += f' {key}="{value}"'
        header += '>\n'
        footer = '</tv>'

        # 写入各电视台文件
        print("⏳ 正在写入各电视台的 EPG 文件...")
        for display_name, programmes in grouped.items():
            safe_name = re.sub(r'[^\w\s-]', '', display_name).strip()
            if not safe_name:
                safe_name = "channel_" + display_name
            channel_dir = os.path.join(output_base_dir, safe_name)
            os.makedirs(channel_dir, exist_ok=True)

            prog_strs = [ET.tostring(prog, encoding='unicode', method='xml') for prog in programmes]
            channel_xml = header + '\n'.join(prog_strs) + '\n' + footer

            file_path = os.path.join(channel_dir, 'epg.xml')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(channel_xml)

            print(f"   ✅ 已写入: {file_path} (共 {len(programmes)} 条节目)")

        print(f"\n🎉 全部完成！文件保存在 '{output_base_dir}' 目录中。")

    except ET.ParseError as e:
        print(f"❌ XML 解析错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
