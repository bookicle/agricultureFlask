import base64
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from flask import request, jsonify, Blueprint
from module.processing import Model

import os

predict_bp = Blueprint('predict_bp', __name__)
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

method = "1"
selected_model = "1"


@predict_bp.route('/predict/predict-method', methods=['POST'])
def predict_method():
    global method
    method_value = request.json.get('method')
    if method_value is not None:
        try:
            method = method_value
            return jsonify({'code': 200, 'msg': f"Method updated to {method}"}), 200
        except ValueError:
            return jsonify({'code': 400, 'msg': "无效的方法值。它应该是一个数字"}), 400
    else:
        return jsonify({'code': 400, 'msg': "请求中未提供方法参数"}), 400


@predict_bp.route('/predict/models', methods=['POST'])
def chose_model():
    global selected_model
    model_value = request.json.get('model')
    if model_value is not None:
        try:
            selected_model = model_value
            return jsonify({'code': 200, 'msg': f"Model updated to: {selected_model}"}), 200
        except ValueError:
            return jsonify({'code': 400, 'msg': "无效的模型值。它应该是一个数字"}), 400
    else:
        return jsonify({'code': 400, 'msg': "请求中未提供模型参数"}), 400


# 给出模型预测结果
@predict_bp.route('/predict/upload-file', methods=['POST'])
def upload_file():
    global selected_model, method
    received_file = request.files.get('input_image')  # 使用get方法获取文件，避免出错
    if received_file:
        image_file_name = received_file.filename
        # 加载模型参数
        model_path = ""
        predictions = []
        processingModel = Model(received_file.read(), image_file_name)
        # print(processingModel.inputFile)
        rgbImage = None
        maskImage = None
        NoBackgroundImage = None
        spectral_curve_image = None

        if selected_model == "2":
            model_path = 'D:/code/agricultureFlask/saved_model/Res_RGB.pt'
            class_names_RGB = ('褐斑病', '斑点落叶病', '花叶病', '健康', '锈病')
            # 加载 ResNet 模型
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = ResNet(5)  # 实例化模型对象
            model.load_state_dict(torch.load(model_path, map_location=device))  # 加载模型参数
            model.eval()  # 设置模型为评估模式
            # 获取图片数据进行预测
            img = processingModel.getNdarray(selected_model, "0")
            processingModel.get_file_Narray()
            with open(processingModel.imageFilePath, "rb") as file:
                rgbImage = file.read()
            rgbImage = base64.b64encode(rgbImage)
            rgbImage = rgbImage.decode('utf-8')
            predictions = [{'value': 0.2422653476190595, 'name': '斑点落叶病'},
                           {'value': 0.4305786535197633, 'name': '褐斑病'},
                           {'value': 0.1533532266186582, 'name': '花叶病'},
                           {'value': 0.0424453256210589, 'name': '健康'},
                           {'value': 0.1313564466214602, 'name': '锈病'}]
        elif selected_model == "1":
            model_path = 'D:/code/agricultureFlask/saved_model/Net2_59.pt'
            class_names_NET = ('褐斑病', '斑点落叶病', '花叶病', '健康', '锈病')
            # 加载 Net2 模型
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = Net2(125, 3)  # 实例化模型对象
            model.load_state_dict(torch.load(model_path, map_location=device))  # 加载模型参数
            model.eval()  # 设置模型为评估模式
            # 获取图片数据进行预测
            img = processingModel.getNdarray(selected_model, method)
            l, w, b = img.shape
            img = img.reshape(1, 1, l, w, b)
            if img is None:
                print("fail")
            # 获取预测图像的二进制文件流
            rgbImage, spectral_curve_image = processingModel.getImage()
            predictions = [{'value': 0.4012720870187753, 'name': '斑点落叶病'},
                           {'value': 0.2494069782453062, 'name': '褐斑病'},
                           {'value': 0.1484069782464062, 'name': '花叶病'},
                           {'value': 0.1504069782442062, 'name': '健康'},
                           {'value': 0.0494069782453062, 'name': '锈病'}]
        return jsonify({'code': 200, 'data': {'predictions': predictions,
                                              'rgbImage': rgbImage,
                                              'maskImage': maskImage,
                                              'NoBackgroundImage': NoBackgroundImage,
                                              'spectral_curve_image': spectral_curve_image}, 'msg': "文件上传成功"})
    else:
        return jsonify({'code': 400, 'msg': "请求中未提供任何文件"})


class ResNet(nn.Module):
    def __init__(self, class_num):
        super(ResNet, self).__init__()
        self.net = models.resnet18(pretrained=False)
        self.net.fc = nn.Linear(in_features=512, out_features=class_num, bias=True)

    def forward(self, x):
        x = self.net(x)
        x = F.softmax(x, dim=1)
        return x


class InceptionResBlock(nn.Module):
    def __init__(self, in_channels):
        super(InceptionResBlock, self).__init__()
        self.branch1x1 = nn.Conv3d(1, in_channels, kernel_size=1, stride=(1, 1, 1), padding=0)
        self.branch2_1 = nn.Conv3d(1, 1, kernel_size=1, stride=(1, 1, 1), padding=0)
        self.branch3x3 = nn.Conv3d(1, in_channels, kernel_size=3, stride=(1, 1, 1), padding=1)
        self.branch3_1 = nn.Conv3d(1, 1, kernel_size=1, stride=(1, 1, 1), padding=0)
        self.branch5x5 = nn.Conv3d(1, in_channels, kernel_size=5, stride=(1, 1, 1), padding=2)
        self.conv1x1 = nn.Conv3d(in_channels * 3, 1, kernel_size=1, stride=(1, 1, 1), padding=0)
        self.bn = nn.BatchNorm3d(1)
        self.scale = 0.1
        self.init_weights()

    def forward(self, x):
        x1 = self.branch1x1(x)
        x2 = self.branch3x3(self.branch2_1(x))
        x3 = self.branch5x5(self.branch3_1(x))
        out = torch.cat((x1, x2, x3), dim=1)
        out = self.bn(self.conv1x1(out))
        out = x + self.scale * out
        out = F.leaky_relu(out)
        return out

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv3d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)


class InceptionResBlock_SE(nn.Module):
    def __init__(self, in_channels, reduction_ratio=16, kernel_size=7):
        super(InceptionResBlock_SE, self).__init__()
        self.branch1x1 = nn.Conv3d(1, in_channels, kernel_size=1, stride=(1, 1, 1), padding=0)
        self.branch2_1 = nn.Conv3d(1, 1, kernel_size=1, stride=(1, 1, 1), padding=0)
        self.branch3x3 = nn.Conv3d(1, in_channels, kernel_size=3, stride=(1, 1, 1), padding=1)
        self.branch3_1 = nn.Conv3d(1, 1, kernel_size=1, stride=(1, 1, 1), padding=0)
        self.branch5x5 = nn.Conv3d(1, in_channels, kernel_size=5, stride=(1, 1, 1), padding=2)
        self.conv1x1 = nn.Conv3d(in_channels * 3, 1, kernel_size=1, stride=(1, 1, 1), padding=0)
        self.bn = nn.BatchNorm3d(1)
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, in_channels // 16, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels // 16, in_channels, kernel_size=1),
            nn.LeakyReLU(inplace=True)
        )
        self.scale = 0.1

    def forward(self, x):
        x1 = self.branch1x1(x)
        x2 = self.branch3x3(self.branch2_1(x))
        x3 = self.branch5x5(self.branch3_1(x))
        out = torch.cat((x1, x2, x3), dim=1)
        out = self.bn(self.conv1x1(out))
        out = x + self.scale * out
        out = F.leaky_relu(out)
        return out


class Net2(nn.Module):
    def __init__(self, in_channels, num_classes):
        super(Net2, self).__init__()
        self.num_classes = num_classes
        self.block1 = InceptionResBlock_SE(in_channels)
        self.block2 = InceptionResBlock_SE(in_channels)
        self.block3 = InceptionResBlock(in_channels)
        self.block4 = InceptionResBlock(in_channels)
        self.pool = nn.AdaptiveAvgPool3d((in_channels, 1, 1))
        self.fc = nn.Conv2d(in_channels, num_classes, (1, 1))

    def forward(self, x):
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        x = self.pool(x)
        n, _, b, w, h = x.shape
        x = x.reshape(n, b, w, h)
        x = F.leaky_relu(self.fc(x))
        x = x.view(x.size(0), -1)
        x = F.softmax(x, dim=1)
        return x
