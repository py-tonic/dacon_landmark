import os
import random
import argparse
import multiprocessing
from tqdm import tqdm, trange
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn 
from torch.utils.data import DataLoader, random_split
from torch.utils.tensorboard import SummaryWriter
import torchvision
import torchvision.transforms as transforms
from dataset import Dacon


#########setting hyperparameters in here########
parser = argparse.ArgumentParser()
parser.add_argument('--mode', default='train')
args = parser.parse_args()

DIR = '/home/ubuntu/jiuk/data/' #nipa server dir
pbar = trange(100, desc='Loss : 0', leave=True, position=0)
BATCH_SIZE = 128
LEARNING_RATE = 1e-3
LR_STEP = 3
LR_FACTOR = 0.5
NUM_CLASSES = 1049
NUM_WORKERS = multiprocessing.cpu_count() #24

torch.manual_seed(777)
torch.cuda.manual_seed(777)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
np.random.seed(777)
random.seed(777)

PARAMETERS = {
    'mean':[0, 0, 0],
    'std': [0, 0, 0]
}
'''
parameter 구하는거 매번 하기 귀찮으니까
일단 밑에거 긁어서 바로 넣으셈
'''
TRAIN_PARAMETERS = {
    'mean':[0.4451, 0.4457, 0.4464],
    'std':[0.2679, 0.2682, 0.2686]
}
TEST_PARAMETERS = {
    'mean':[0.4456, 0.4462, 0.4468],
    'std':[0.2757, 0.2769, 0.2763]

}
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print('use: ',device)
################################################
train_acc_list = []
valid_acc_list = []
train_loss_list = []
valid_loss_list = []

calculation = transforms.Compose([
    transforms.ToTensor()
])

def get_parameters(dataset):
    '''
    It takes about 5 minutes
    '''

    dataloader = DataLoader(dataset, batch_size = BATCH_SIZE, num_workers=NUM_WORKERS)
    count = 0
    if args.mode == 'train':
        for images, _ in tqdm(dataloader):
            import pdb; pdb.set_trace()
            for i in range(3):
                var = images[:,:,:,i].view(-1)
                PARAMETERS['mean'][i] += var.mean()
                PARAMETERS['std'][i] += var.std()
            count += 1
    else:
        for images in tqdm(dataloader):
            for i in range(3):
                var = images[:,:,:,i].view(-1)
                PARAMETERS['mean'][i] += var.mean()
                PARAMETERS['std'][i] += var.std()
            count += 1

    for i in range(3):
        PARAMETERS['mean'][i] /= count
        PARAMETERS['std'][i] /= count

    print('Calculation Completed')
    print(PARAMETERS)
    return PARAMETERS

def train(train_loader, model, criterion, optimizer, epoch, lr_scheduler):
    print(f'epoch: {epoch}')
    model.train()
    train_acc = 0
    for images, labels in train_loader:
        optimizer.zero_grad()
        output = model(images.to(device))
        loss = criterion(output, labels.to(device))
        loss.backward()
        optimizer.step()
        train_acc += (output.argmax(1)==labels).float().mean()
        pbar.set_description("Loss : %.3f" % loss)
    return train_acc, loss

def inference(valid_loader, model, criterion):
    model.eval()
    valid_acc = 0
    for images, labels in valid_loader:
        with torch.no_grad():
            output = model(images.to(device))
            loss = criterion(output, labels)
            valid_acc += (output.argmax(1)==labels).float().mean()
    return valid_acc, loss

def generate_submission():
    pass

def visualize(img, one_channel=False):
    if one_channel:
        img = img.mean(dim=0)
    img = img/2+0.5
    npimg = img.numpy()
    if one_channel:
        plt.imshow(npimg, cmap='Greys')
    else:
        plt.imshow(np.transpose(npimg, (1,2,0)))

if __name__ == '__main__':
    cal_dataset = Dacon(dir=DIR, mode=args.mode, transform=calculation)
    PARAMETERS = get_parameters(cal_dataset)

    transforms_train = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
        transforms.Normalize(PARAMETERS['mean'], PARAMETERS['std'])
    ])
    writer = SummaryWriter('runs/dacon')
    dacon = Dacon(dir=DIR, mode=args.mode, transform=transforms_train)
    dataloader = DataLoader(dacon, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)
    dataiter = iter(dataloader)
    images, labels = dataiter.next()
    img_grid = torchvision.utils.make_grid(images)
    visualize(img_grid)
    writer.add_image('dacon_image', img_grid)

    '''
    transforms_train = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN,STD)
    ])
    dacon = Dacon(dir=DIR, mode=args.mode, transform=transforms_train)
    num_train = int(len(dacon) * 0.8)
    num_valid = len(dacon) - num_train
    trainset, validset = random_split(dacon, [num_train, num_valid])
    print(len(dacon))
    trainloader = DataLoader(trainset, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)
    validloader = DataLoader(validset, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)

    model = torchvision.models.resnet18(pretrained=True)
    for param in model.parameters():
        param.requires_grad = False
    model.avg_pool = nn.AdaptiveAvgPool2d(1)
    model.fc = nn.Linear(model.fc.in_features, NUM_CLASSES)
    model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=LR_STEP, gamma=LR_FACTOR)

    for epoch in pbar:
        train_acc, train_loss = train(trainloader, model, criterion, optimizer, epoch, lr_scheduler)
        lr_scheduler.step()
        train_acc_list.append(train_acc/len(trainloader))
        train_loss_list.append(train_loss.detach.cpu().numpy())

        valid_acc, valid_loss = inference(validloader, model, criterion, optimizer, epoch, lr_scheduler)
        valid_acc_list.append(valid_acc/len(validloader))
        valid_loss_list.append(valid_loss.detach.cpu().numpy())
    '''