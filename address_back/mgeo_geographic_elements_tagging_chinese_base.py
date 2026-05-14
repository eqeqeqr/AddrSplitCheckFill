from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import os

class MGeoElementsTagging:
    """
    地理实体命名实体识别址结构化要素解析工具类
    程序启动时初始化一次，后续直接调用，无需重复加载模型
    """
    def __init__(self):

        # 项目根目录（可根据实际项目修改）
        self.project_root = r"C:\Users\Administrator\Desktop\address_project"
        self.task = Tasks.token_classification
        # 拼接模型路径（自动处理路径分隔符，跨平台兼容）
        self.model_path = os.path.join(self.project_root, "address_back","iic", "mgeo_geographic_elements_tagging_chinese_base")
        
        # 初始化时就加载模型（只加载一次）
        self.pipeline_ins = pipeline(
            task=self.task,
            model=self.model_path,
            model_revision='master'
        )
        print("🔥 MGeo门址地址结构化要素解析-中文-地址领域-base模型 初始化完成！")

    def parse(self, inputs: str) -> list:
        """
        对外提供的调用方法，直接传入文本即可识别
        :param inputs: 待识别的地址文本
        :return: 实体识别结果
        """
        if not inputs or not isinstance(inputs, str):
            return []
        return self.pipeline_ins(input=inputs)
        
    # ====================== 给别人调用的统一方法 ======================
    def get_elements_tagging(self, input_text: str) -> list:
        """
        外部调用入口（最简单的调用方式）
        使用示例：result = get_elements_tagging("浙江省杭州市余杭区阿里巴巴西溪园区")
        """
        # 1. 获取原始结果
        raw_result = self.parse(input_text)
        
        # 2. 只在这里解析 WHERE 和 WHAT
        tmp={}
        for item in raw_result['output']:
                tmp[item['type']]=item['span']
        init_result_fileds={
        'prov':'',#解释：省级行政区划，省、自治区、直辖市
        'city':'',#解释：地级行政区划，地级市、地区、自治州等
        'district':'',#解释：县级行政区划，市辖区、县级市、县等
        'devzone':'',#解释：广义的上的开发区，除国家级、省级等具备一定行政职能的开发区外，一般性产业园区、度假区等也应标注为开发区
        'town':'',#解释：乡级行政区划，镇、街道、乡等
        'community':'',#解释：包含社区、行政村（生产大队、村委会），自然村
        'village_group':'',#解释：限定xx组、xx队、xx社（xx为数字）
        'road':'',#解释：有正式名称的道路，包括隧道、高架、街、弄、巷等
        'roadno':'',#解释：路号
        'poi':'',#解释：兴趣点
        'subpoi':'',#解释：子兴趣点
        'houseno':'',#解释：楼栋号，农村地址的门牌号(包括类似南楼、北楼一类的描述)
        'cellno':'',#解释：单元号
        'floorno':'',#解释：楼层号
        'roomno':'',#解释：房间号、户号
        'detail':'',#解释：poi内部的四层关系（house,cell,floor, room）没明确是哪一层，如xx-xx-x-x，则整体标注detail
        'assist':'',#解释：普通辅助定位词
        'distance':'',#解释：距离辅助定位词，比如"716县道北50米"中的50米，具有具体数字
        'intersection':'',#解释：道路口，口、交叉口、道路（高速）出入口
        'redundant':'',#解释：非地址元素，如配送提示、配送要求、友情提醒或威胁等
        'others':'',#解释：以上标签未覆盖的情况，或者无法判断的地址元素 
        }
        # 3. 把官方返回的值 覆盖到 完整字段里
        for key in init_result_fileds:
            if key in tmp:
                init_result_fileds[key] = tmp[key]

        # 4. 返回完整字段（永远包含所有key，没有值就是None）
        return init_result_fileds
        

# ====================== 全局初始化（在程序启动时执行一次） ======================
# 全局单例，启动时就加载好模型，后续所有调用都使用这个实例
# geo_recognizer = MeoElementsTagging()



# ====================== 测试调用 ======================
if __name__ == '__main__':
    # 别人只需要这样调用
    test_input = "浙江省湖州市安吉县昌硕街道灵芝社区灵芝西路358号汇丰花园北苑7幢"
    geo_recognizer = MGeoElementsTagging()
    result = geo_recognizer.get_elements_tagging(test_input)
    print("识别结果：", result)