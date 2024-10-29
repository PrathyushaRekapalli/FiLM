from data_provider.data_factory import data_provider
from exp.exp_basic import Exp_Basic
from models import Informer, Autoformer, Transformer, Logformer, Reformer,AE
# from models.reformer_pytorch.reformer_pytorch import Reformer
from utils.tools import EarlyStopping, adjust_learning_rate, visual
from utils.metrics import metric

import numpy as np
import torch
import torch.nn as nn
from torch import optim

import os
import time

import warnings
import matplotlib.pyplot as plt
import numpy as np
import io
from scipy import stats
warnings.filterwarnings('ignore')

compress_len=64

class Exp_Main(Exp_Basic):
    def __init__(self, args):
        super(Exp_Main, self).__init__(args)

    def _build_model(self):
        model_dict = {
            'Autoformer': Autoformer,
            'Transformer': Transformer,
            'Informer': Informer,
            'Reformer': Reformer,
            'Logformer': Logformer,
            'AE':AE
        }
        model = model_dict[self.args.model].Model(self.args).float()

        if self.args.use_multi_gpu and self.args.use_gpu:
            model = nn.DataParallel(model, device_ids=self.args.device_ids)
        return model

    def _get_data(self, flag):
        data_set, data_loader = data_provider(self.args, flag)
        return data_set, data_loader

    def _select_optimizer(self):
        model_optim = optim.Adam(self.model.parameters(), lr=self.args.learning_rate)
        return model_optim

    def _select_criterion(self):
        criterion = nn.MSELoss()
        return criterion

    def vali(self, vali_data, vali_loader, criterion):
        total_loss = []
        ks_test_96,ks_test_192,ks_test_336,ks_test_720,ks_test_96_back=[],[],[],[],[]
        ks_result=[]
        ks_test_96_raw,ks_test_192_raw,ks_test_336_raw,ks_test_720_raw,ks_test_96_back_raw=[],[],[],[],[]
        self.model.eval()
        input_len=720
        with torch.no_grad():
            for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(vali_loader):
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_x.float().to(self.device)
                batch_y = torch.cat([torch.zeros_like(batch_y[:, :self.args.label_len, :]),batch_y],dim=1).float()
                #batch_y = batch_y.float()

                batch_x_mark = batch_x_mark.float().to(self.device)
                batch_y_mark = batch_x_mark.float().to(self.device)
                
                dec_inp0=torch.zeros_like(batch_y[:, -compress_len:, :]).float()
                batch_y_mark0 = torch.zeros_like(batch_y_mark[:,-compress_len:,:]).float()
                
                #batch_y_mark = torch.cat([torch.zeros_like(batch_y_mark[:,:self.args.label_len,:]),batch_y_mark],dim=1).float()
                #batch_y_mark = batch_y_mark.float().to(self.device)

                # decoder input
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()

                #dec_inp = torch.cat([torch.zeros_like(batch_y[:, :self.args.label_len, :]).float(), dec_inp], dim=1).float().to(self.device)
                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0, dec_inp, batch_y_mark)[0]
                        else:
                            outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0, dec_inp, batch_y_mark)
                else:
                    if self.args.output_attention:
                        outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0, dec_inp, batch_y_mark)[0]
                    else:
                        outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0, dec_inp, batch_y_mark)
                f_dim = -1 if self.args.features == 'MS' else 0
                batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)

                pred = outputs.detach().cpu()
                true = batch_y.detach().cpu()

                loss = criterion(pred, true)

                total_loss.append(loss)

#                 pred = outputs.detach().cpu().numpy()
#                 true = batch_y.detach().cpu().numpy()
#                 input_data = batch_x.detach().cpu().numpy()
#                 input_len = input_data.shape[1]
#                 for j in range(input_data.shape[0]):
#                     ks_test_96_back.append(stats.kstest(pred[j,-96:,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)
#                     ks_test_96.append(stats.kstest(pred[j,:96,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)
#                     ks_test_192.append(stats.kstest(pred[j,:192,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)
#                     ks_test_336.append(stats.kstest(pred[j,:336,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)
#                     ks_test_720.append(stats.kstest(pred[j,:,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)

#                     ks_test_96_back_raw.append(stats.kstest(true[j,-96:,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)
#                     ks_test_96_raw.append(stats.kstest(true[j,:96,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)
#                     ks_test_192_raw.append(stats.kstest(true[j,:192,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)
#                     ks_test_336_raw.append(stats.kstest(true[j,:336,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)
#                     ks_test_720_raw.append(stats.kstest(true[j,:,-1:].reshape(-1),input_data[j,:,-1:].reshape(-1)).pvalue)
#                 if i==0:
#                         pred = outputs.detach().cpu().numpy()
#                         true = batch_y.detach().cpu().numpy()
#                         input_data = batch_x.detach().cpu().numpy()
#                         plt.cla()
#                         plot_index1=np.arange(input_data.shape[1])
#                         plot_index2=np.arange(input_data.shape[1],input_data.shape[1]+pred.shape[1])
#                         plt.plot(plot_index1,input_data[0,:,-1:],label='input')
#                         plt.plot(plot_index2,pred[0,:,-1:],label="predict")
#                         plt.plot(plot_index2,true[0,:,-1:],label="true")

#                         plt.legend()
#                         #f = io.BytesIO()
#                         plt.savefig(self.args.model+'_'+self.args.data+"_sample0.png",format="png")
#                         #plt.clf()
#                         plt.cla()
#                         plt.plot(plot_index1,input_data[8,:,-1:],label='input')
#                         plt.plot(plot_index2,pred[8,:,-1:],label="predict")
#                         plt.plot(plot_index2,true[8,:,-1:],label="true")
#                         plt.legend()
#                         plt.savefig(self.args.model+'_'+self.args.data+"_sample1.png",format="png")

#         import pickle
#         ks_result.append(ks_test_96_back)
#         ks_result.append(ks_test_96)
#         ks_result.append(ks_test_192)
#         ks_result.append(ks_test_336)
#         ks_result.append(ks_test_720)
#         ks_result.append(ks_test_96_back_raw)
#         ks_result.append(ks_test_96_raw)
#         ks_result.append(ks_test_192_raw)
#         ks_result.append(ks_test_336_raw)
#         ks_result.append(ks_test_720_raw)
#         with open(self.args.model+'_'+self.args.data+'_ks_test.pkl','wb') as f:
#             pickle.dump(ks_result,f)
#         print('mean ks 96 back',np.mean(ks_test_96_back))
#         print('mean ks 96 ',np.mean(ks_test_96))
#         print('mean ks 192 ',np.mean(ks_test_192))
#         print('mean ks 336 ',np.mean(ks_test_336))
#         print('mean ks 720 ',np.mean(ks_test_720))

#         print('mean raw ks 96 back',np.mean(ks_test_96_back_raw))
#         print('mean raw ks 96 ',np.mean(ks_test_96_raw))
#         print('mean raw ks 192 ',np.mean(ks_test_192_raw))
#         print('mean raw ks 336 ',np.mean(ks_test_336_raw))
#         print('mean raw ks 720 ',np.mean(ks_test_720_raw))

#         print('mean ks relative 96 back',np.mean(ks_test_96_back)/np.mean(ks_test_96_back_raw))
#         print('mean ks relative 96 ',np.mean(ks_test_96)/np.mean(ks_test_96_raw))
#         print('mean ks relative 192 ',np.mean(ks_test_192)/np.mean(ks_test_192_raw))
#         print('mean ks relative 336 ',np.mean(ks_test_336)/np.mean(ks_test_336_raw))
#         print('mean ks relative 720 ',np.mean(ks_test_720)/np.mean(ks_test_720_raw))
#         raise Exception('aaa')
        total_loss = np.average(total_loss)
        self.model.train()
        return total_loss

    def train(self, setting):
        train_data, train_loader = self._get_data(flag='train')
        vali_data, vali_loader = self._get_data(flag='val')
        test_data, test_loader = self._get_data(flag='test')

        path = os.path.join(self.args.checkpoints, setting)
        if not os.path.exists(path):
            os.makedirs(path)

        time_now = time.time()

        train_steps = len(train_loader)
        early_stopping = EarlyStopping(patience=self.args.patience, verbose=True)

        model_optim = self._select_optimizer()
        criterion = self._select_criterion()

        if self.args.use_amp:
            scaler = torch.cuda.amp.GradScaler()

        for epoch in range(self.args.train_epochs):
            iter_count = 0
            train_loss = []

            self.model.train()
            epoch_time = time.time()
            for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(train_loader):
                iter_count += 1
                model_optim.zero_grad()
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_x.float().to(self.device)
                batch_y = torch.cat([torch.zeros_like(batch_y[:, :self.args.label_len, :]),batch_y],dim=1).float()
                


                #batch_y = batch_y.float().to(self.device)
                batch_x_mark = batch_x_mark.float().to(self.device)
                batch_y_mark = batch_x_mark.float().to(self.device)
                #batch_y_mark = torch.cat([torch.zeros_like(batch_y_mark[:,:self.args.label_len,:]),batch_y_mark],dim=1).float()
                #batch_y_mark = batch_y_mark.float().to(self.device)

                # decoder input
                dec_inp0=torch.zeros_like(batch_y[:, -compress_len:, :]).float()
                batch_y_mark0 = torch.zeros_like(batch_y_mark[:,-compress_len:,:]).float()
                
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
                #dec_inp = torch.cat([torch.zeros_like(batch_y[:, :self.args.label_len, :]).float(), dec_inp], dim=1).float().to(self.device)

                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0, dec_inp, batch_y_mark)[0]
                        else:
                            outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0, dec_inp, batch_y_mark)

                        f_dim = -1 if self.args.features == 'MS' else 0
                        batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)
                        loss = criterion(outputs, batch_y)
                        train_loss.append(loss.item())
                else:
                    if self.args.output_attention:
                        outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0, dec_inp, batch_y_mark)[0]
                    else:
                        outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0, dec_inp, batch_y_mark, batch_y)

                    f_dim = -1 if self.args.features == 'MS' else 0
                    batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)

#                     if i==0:
#                         from scipy import stats
#                         pred = outputs.detach().cpu().numpy()
#                         true = batch_y.detach().cpu().numpy()
#                         input_data = batch_x.detach().cpu().numpy()
#                         plot_index1=np.arange(input_data.shape[1])
#                         plot_index2=np.arange(input_data.shape[1],input_data.shape[1]+pred.shape[1])
#                         plt.cla()
#                         plt.plot(plot_index1,input_data[0,:,-1:],label='input')
#                         plt.plot(plot_index2,pred[0,:,-1:],label="predict")
#                         plt.plot(plot_index2,true[0,:,-1:],label="true")
#                         print('KS test1',stats.kstest(input_data[0,:,-1:].reshape(-1),pred[0,-input_data.shape[1]:,-1:].reshape(-1)))

#                         plt.legend()
#                         #f = io.BytesIO()
#                         plt.savefig("sample0.png",format="png")
#                         #plt.clf()
#                         plt.cla()
#                         plt.plot(plot_index1,input_data[8,:,-1:],label='input')
#                         plt.plot(plot_index2,pred[8,:,-1:],label="predict")
#                         plt.plot(plot_index2,true[8,:,-1:],label="true")
#                         plt.legend()
#                         plt.savefig("sample1.png",format="png")
#                         print('KS test2',stats.kstest(input_data[8,:,-1:].reshape(-1),pred[8,-input_data.shape[1]:,-1:].reshape(-1)))
#                         raise Exception('aaa')


                    loss = criterion(outputs, batch_y)
                    train_loss.append(loss.item())

                if (i + 1) % 100 == 0:
                    # print("\titers: {0}, epoch: {1} | loss: {2:.7f}".format(i + 1, epoch + 1, loss.item()))
                    speed = (time.time() - time_now) / iter_count
                    left_time = speed * ((self.args.train_epochs - epoch) * train_steps - i)
                    # print('\tspeed: {:.4f}s/iter; left time: {:.4f}s'.format(speed, left_time))
                    iter_count = 0
                    time_now = time.time()

                if self.args.use_amp:
                    scaler.scale(loss).backward()
                    scaler.step(model_optim)
                    scaler.update()
                else:
                    loss.backward()
                    model_optim.step()

            print("Epoch: {} cost time: {}".format(epoch + 1, time.time() - epoch_time))
            train_loss = np.average(train_loss)
            vali_loss = self.vali(vali_data, vali_loader, criterion)
            test_loss = self.vali(test_data, test_loader, criterion)

            print("Epoch: {0}, Steps: {1} | Train Loss: {2:.7f} Vali Loss: {3:.7f} Test Loss: {4:.7f}".format(
                epoch + 1, train_steps, train_loss, vali_loss, test_loss))
            early_stopping(vali_loss, self.model, path)
            if early_stopping.early_stop:
                print("Early stopping")
                break

            adjust_learning_rate(model_optim, epoch + 1, self.args)

        best_model_path = path + '/' + 'checkpoint.pth'
        self.model.load_state_dict(torch.load(best_model_path))

        return self.model

    def test(self, setting, test=0):
        test_data, test_loader = self._get_data(flag='test')
        if test:
            print('loading model')
            self.model.load_state_dict(torch.load(os.path.join('./checkpoints/' + setting, 'checkpoint.pth')))

        preds = []
        trues = []
        folder_path = './test_results/' + setting + '/'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        self.model.eval()
        with torch.no_grad():
            for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(test_loader):
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_x.float().to(self.device)
                batch_y = torch.cat([torch.zeros_like(batch_y[:, :self.args.label_len, :]),batch_y],dim=1).float()

                #batch_y = batch_y.float().to(self.device)

                batch_x_mark = batch_x_mark.float().to(self.device)
                batch_y_mark = batch_x_mark.float().to(self.device)
                #batch_y_mark = torch.cat([torch.zeros_like(batch_y_mark[:,:self.args.label_len,:]),batch_y_mark],dim=1).float()
                #batch_y_mark = batch_y_mark.float().to(self.device)
                dec_inp0=torch.zeros_like(batch_y[:, -compress_len:, :]).float()
                batch_y_mark0 = torch.zeros_like(batch_y_mark[:,-compress_len:,:]).float()

                # decoder input
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
                #dec_inp = torch.cat([torch.zeros_like(batch_y[:, :self.args.label_len, :]).float(), dec_inp], dim=1).float().to(self.device)
                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0,  dec_inp, batch_y_mark)[0]
                        else:
                            outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0,  dec_inp, batch_y_mark)
                else:
                    if self.args.output_attention:
                        outputs = self.model(batch_x, batch_x_mark, dec_inp0,batch_y_mark0, dec_inp, batch_y_mark)[0]

                    else:
                        outputs = self.model(batch_x, batch_x_mark,dec_inp0,batch_y_mark0,  dec_inp, batch_y_mark)

                f_dim = -1 if self.args.features == 'MS' else 0

                batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)
                outputs = outputs.detach().cpu().numpy()
                batch_y = batch_y.detach().cpu().numpy()

                pred = outputs  # outputs.detach().cpu().numpy()  # .squeeze()
                true = batch_y  # batch_y.detach().cpu().numpy()  # .squeeze()

                preds.append(pred)
                trues.append(true)
                if i % 20 == 0:
                    input = batch_x.detach().cpu().numpy()
                    gt = np.concatenate((input[0, :, -1], true[0, :, -1]), axis=0)
                    pd = np.concatenate((input[0, :, -1], pred[0, :, -1]), axis=0)
                    visual(gt, pd, os.path.join(folder_path, str(i) + '.pdf'))

        preds = np.array(preds)
        trues = np.array(trues)
        print('test shape:', preds.shape, trues.shape)
        preds = preds.reshape(-1, preds.shape[-2], preds.shape[-1])
        trues = trues.reshape(-1, trues.shape[-2], trues.shape[-1])
        print('test shape:', preds.shape, trues.shape)

        # result save
        folder_path = './results/' + setting + '/'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        mae, mse, rmse, mape, mspe = metric(preds, trues)
        print('mse:{}, mae:{}'.format(mse, mae))
        f = open("result.txt", 'a')
        f.write(setting + "  \n")
        f.write('mse:{}, mae:{}'.format(mse, mae))
        f.write('\n')
        f.write('\n')
        f.close()

        np.save(folder_path + 'metrics.npy', np.array([mae, mse, rmse, mape, mspe]))
        np.save(folder_path + 'pred.npy', preds)
        np.save(folder_path + 'true.npy', trues)

        return

    def predict(self, setting, load=False):
        pred_data, pred_loader = self._get_data(flag='pred')

        if load:
            path = os.path.join(self.args.checkpoints, setting)
            best_model_path = path + '/' + 'checkpoint.pth'
            self.model.load_state_dict(torch.load(best_model_path))

        preds = []

        self.model.eval()
        with torch.no_grad():
            for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(pred_loader):
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_x.float().to(self.device)
                batch_y = torch.cat([torch.zeros_like(batch_y[:, :self.args.label_len, :]),batch_y],dim=1).float()

                #batch_y = batch_y.float()
                batch_x_mark = batch_x_mark.float().to(self.device)
                #batch_y_mark = batch_y_mark.float().to(self.device)
                batch_y_mark = batch_x_mark.float().to(self.device)
                dec_inp0=torch.zeros_like(batch_y[:, -compress_len:, :]).float()
                batch_y_mark0 = torch.zeros_like(batch_y_mark[:,-compress_len:,:]).float()
                #batch_y_mark = torch.cat([torch.zeros_like(batch_y_mark[:,:self.args.label_len,:]),batch_y_mark],dim=1).float()

                # decoder input
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
                #dec_inp = torch.cat([torch.zeros_like(batch_y[:, :self.args.label_len, :]).float(), dec_inp], dim=1).float().to(self.device)
                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp0,batch_y_mark0,  dec_inp, batch_y_mark)[0]
                        else:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp0,batch_y_mark0,  dec_inp, batch_y_mark)
                else:
                    if self.args.output_attention:
                        outputs = self.model(batch_x, batch_x_mark, dec_inp0,batch_y_mark0,  dec_inp, batch_y_mark)[0]
                    else:
                        outputs = self.model(batch_x, batch_x_mark, dec_inp0,batch_y_mark0,  dec_inp, batch_y_mark)
                pred = outputs.detach().cpu().numpy()  # .squeeze()
                preds.append(pred)

        preds = np.array(preds)
        preds = preds.reshape(-1, preds.shape[-2], preds.shape[-1])

        # result save
        folder_path = './results/' + setting + '/'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        np.save(folder_path + 'real_prediction.npy', preds)

        return
