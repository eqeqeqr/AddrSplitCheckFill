from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import os

class MGeoWhereWhatCut:
    """
    地理地点WhereWhat切分工具类
    程序启动时初始化一次，后续直接调用，无需重复加载模型
    """
    def __init__(self):

        # 项目根目录（可根据实际项目修改）
        self.project_root = r"C:\Users\Administrator\Desktop\address_project"
        self.task = Tasks.token_classification
        # 拼接模型路径（自动处理路径分隔符，跨平台兼容）
        self.model_path = os.path.join(self.project_root, "address_back","iic", "mgeo_geographic_where_what_cut_chinese_base")
        
        # 初始化时就加载模型（只加载一次）
        self.pipeline_ins = pipeline(
            task=self.task,
            model=self.model_path,
            model_revision='master'
        )
        print("🔥 MGeo地址地点WhereWhat切分-中文-地址领域-base模型 初始化完成！")

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
    def get_where_what(self, input_text: str) -> list:
        """
        外部调用入口（最简单的调用方式）
        使用示例：result = get_wherewhat("浙江省杭州市余杭区阿里巴巴西溪园区")
        """
        # 1. 获取原始结果
        raw_result = self.parse(input_text)
        
        # 2. 只在这里解析 WHERE 和 WHAT
        where = None
        what = None

        if raw_result and 'output' in raw_result:
            for item in raw_result['output']:
                typ = item.get('type')
                span = item.get('span', '').strip()
                if typ == '/WHERE':
                    where = span
                elif typ == '/WHAT':
                    what = span

        # 3. 返回你要的格式
        return {"where": where, "what": what}
    

# ====================== 全局初始化（在程序启动时执行一次） ======================
# 全局单例，启动时就加载好模型，后续所有调用都使用这个实例
# geo_recognizer = GeoEntityRecognition()




# ====================== 测试调用 ======================
if __name__ == '__main__':
    # 别人只需要这样调用
    test_input = "浙江省杭州市余杭区阿里巴巴西溪园区"
    geo_recognizer = MGeoWhereWhatCut()
    result = geo_recognizer.get_where_what(test_input)
    print("识别结果：", result)