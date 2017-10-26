import cv2
import numpy as np
import tensorflow as tf

from ops import batch_normal
from ops import conv2d
from ops import conv_cond_concat
from ops import de_conv
from ops import fully_connect
from ops import lrelu
from utils import load_mnist
from utils import sample_label
from utils import save_images
from utils import vis_square

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from tensorflow.examples.tutorials.mnist import input_data

learning_rate = 0.0002
batch_size = 128
EPOCH = 5
display_step = 1
sample_size = 100
#sample_size = 16
y_dim = 10
channel = 1


def getNext_batch(input , data_y , batch_num):
    return input[(batch_num)*batch_size : (batch_num  + 1)*batch_size] \
        , data_y[(batch_num)*batch_size : (batch_num + 1)*batch_size]

def shuffle_data(input , data_y):
    random_permutation = np.random.permutation(len(input))
    return input[random_permutation], data_y[random_permutation]

def plot(samples):
    fig = plt.figure(figsize=(4, 4))
    gs = gridspec.GridSpec(4, 4)
    gs.update(wspace=0.05, hspace=0.05)

    for i, sample in enumerate(samples):
        ax = plt.subplot(gs[i])
        plt.axis('off')
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_aspect('equal')
        plt.imshow(sample.reshape(28, 28), cmap='Greys_r')

def dcgan(operation , data_name , output_size , sample_path , log_dir , model_path , visua_path , sample_num = 16):

    if data_name ==  "fashion_mnist":

        print("you use the fashion mnist dataset")

        data_array , data_y = load_mnist(data_name)
        #f_mnist = input_data.read_data_sets('./data/fashion_mnist', one_hot=True)

        sample_z = np.random.uniform(-1 , 1 , size = [sample_num , 100])

        y = tf.placeholder(tf.float32, [None , y_dim])

        images = tf.placeholder(tf.float32, [batch_size, output_size, output_size, channel])

        z = tf.placeholder(tf.float32, [None , sample_size])
        z_sum = tf.summary.histogram("z", z)

        fake_images = gern_net(batch_size, z , y ,  output_size)
        G_image = tf.summary.image("G_out", fake_images)

        sample_img = sample_net(sample_num , z , y  , output_size)


        ##the loss of gerenate network
        D_pro , D_logits = dis_net(images, y ,  weights, biases , False)
        D_pro_sum = tf.summary.histogram("D_pro", D_pro)

        G_pro, G_logits = dis_net(fake_images , y ,  weights, biases , True)
        G_pro_sum = tf.summary.histogram("G_pro", G_pro)

        D_fake_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.zeros_like(G_pro), logits=G_logits))
        real_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.ones_like(D_pro), logits=D_logits))
        G_fake_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.ones_like(G_pro),logits=G_logits))

        loss = real_loss + D_fake_loss

        loss_sum = tf.summary.scalar("D_loss", loss)
        G_loss_sum = tf.summary.scalar("G_loss", G_fake_loss)

        merged_summary_op_d = tf.summary.merge([loss_sum, D_pro_sum])
        merged_summary_op_g = tf.summary.merge([G_loss_sum, G_pro_sum, G_image, z_sum])

        t_vars = tf.trainable_variables()

        d_var = [var for var in t_vars if 'dis' in var.name]
        g_var = [var for var in t_vars if 'gen' in var.name]

        saver = tf.train.Saver()

        #if train
        if operation == 0:

            opti_D = tf.train.AdamOptimizer(learning_rate=learning_rate , beta1=0.5).minimize(loss , var_list=d_var)
            opti_G = tf.train.AdamOptimizer(learning_rate=learning_rate , beta1=0.5).minimize(G_fake_loss , var_list=g_var)

            init = tf.global_variables_initializer()

            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True
            i=0

            with tf.Session(config=config) as sess:

                sess.run(init)
                summary_writer = tf.summary.FileWriter(log_dir , graph=sess.graph)
                batch_num = 0
                e = 0
                step = 0

                while e <= EPOCH:
                    data_array , data_y  = shuffle_data(data_array, data_y)
                    while batch_num < len(data_array) / batch_size:

                        step = step + 1

                        realbatch_array , real_labels = getNext_batch(data_array , data_y , batch_num)

                        #Get the z

                        batch_z = np.random.uniform(-1 , 1 , size=[batch_size , sample_size])
                        #batch_z = np.random.normal(0 , 0.2 , size=[batch_size , sample_size])

                        _, summary_str = sess.run([opti_D, merged_summary_op_d],
                                                  feed_dict={images:realbatch_array, z:batch_z , y:real_labels})
                        summary_writer.add_summary(summary_str , step)

                        _, summary_str = sess.run([opti_G, merged_summary_op_g], feed_dict={z: batch_z , y:real_labels})
                        summary_writer.add_summary(summary_str , step)

                        batch_num += 1
                        # average_loss += loss_value

                        if step % display_step == 0:

                            D_loss = sess.run(loss , feed_dict = {images:realbatch_array , z:batch_z , y:real_labels})
                            fake_loss = sess.run(G_fake_loss , feed_dict = {z: batch_z , y:real_labels})
                            print("EPOCH %d step %d: D: loss = %.7f G: loss=%.7f " % (e , step , D_loss , fake_loss))

                        if np.mod(step , 50) == 1:

                            print("sample!")
                            sample_images = sess.run(sample_img , feed_dict={z:sample_z , y:sample_label()})
                            #sample_images = sess.run(fake_images, feed_dict={z: sample_z, y: sample_label()})
                            #save_images(sample_images , [4 , 4] , './{}/train_{:02d}_{:04d}.png'.format(sample_path , e , step))

                            fig = plot(sample_images)
                            plt.savefig('./{}/{}.png'.format(sample_path,str(i).zfill(3)), bbox_inches='tight')
                            i += 1
                            #plt.close(fig)

                            save_path = saver.save(sess, model_path)

                    e = e + 1
                    batch_num = 0

                save_path = saver.save(sess , model_path)
                print("Model saved in file: %s" % save_path)

        #test

        elif operation == 1:

            print("Test")

            init = tf.initialize_all_variables()

            with tf.Session() as sess:

                sess.run(init)

                saver.restore(sess , model_path)
                sample_z = np.random.uniform(1 , -1 , size=[sample_num , 100])

                output = sess.run(sample_img , feed_dict={z:sample_z , y:sample_label()})

                save_images(output , [8 , 8] , './{}/test{:02d}_{:04d}.png'.format(sample_path , 0 , 0))

                image = cv2.imread('./{}/test{:02d}_{:04d}.png'.format(sample_path , 0 , 0) , 0)

                cv2.imshow( "test" , image)

                cv2.waitKey(-1)

                print("Test finish!")

        #visualize
        else:

            print("Visualize")

            init = tf.initialize_all_variables()
            with tf.Session() as sess:

                sess.run(init)

                saver.restore(sess, model_path)

                # visualize the weights 1 or you can change weights_2 .
                conv_weights = sess.run([tf.get_collection('weight_2')])

                vis_square(visua_path , conv_weights[0][0].transpose(3, 0, 1, 2), type=1)

                # visualize the activation 1
                ac = sess.run([tf.get_collection('ac_2')], feed_dict={images: data_array[:64], z:sample_z , y:sample_label()})

                vis_square(visua_path , ac[0][0].transpose(3, 1, 2, 0), type=0)

                print("the visualization finish!")

    else:
        print("other dataset!")

#####generate network

weights2 = {

    'wd': tf.Variable(tf.random_normal([sample_size + y_dim , 1024] , stddev=0.02) , name='genw1') ,
    'wc1': tf.Variable(tf.random_normal([1024 + y_dim , 7*7*2*64], stddev=0.02) , name='genw2'),
    'wc2': tf.Variable(tf.random_normal([5 , 5 , 128 ,  138], stddev=0.02) , name='genw3'),
    'wc3': tf.Variable(tf.random_normal([5 , 5 , channel ,  138], stddev=0.02) , name='genw4') ,

}

biases2 = {

    'bd': tf.Variable(tf.zeros([1024]) , name='genb1') ,
    'bc1': tf.Variable(tf.zeros([7*7*2*64]) , name='genb2'),
    'bc2': tf.Variable(tf.zeros([128]) , name='genb3'),
    'bc3': tf.Variable(tf.zeros([channel]) , name='genb4'),
    
}

def gern_net(batch_size , z , y , output_size):

    yb = tf.reshape(y, shape=[batch_size, 1, 1, y_dim])


    z = tf.concat([z , y] , 1)



    c1 , c2  =  int(output_size/4) , int(output_size/2)

    #10 stand for the num of labels
    d1 = fully_connect(z , weights2['wd'] , biases2['bd'])
    d1 = batch_normal(d1 , scope="genbn1")
    d1 = tf.nn.relu(d1)

    d1 = tf.concat([d1 , y] , 1)

    d2 = fully_connect(d1 , weights2['wc1'] , biases2['bc1'])
    d2 = batch_normal(d2 , scope="genbn2")

    d2 = tf.nn.relu(d2)
    d2 = tf.reshape(d2 , [batch_size , c1 , c1 , 64*2])

    d2 = conv_cond_concat(d2 , yb)

    d3 = de_conv(d2 , weights2['wc2'] , biases2['bc2'] , out_shape=[batch_size , c2 , c2 , 128])
    d3 = batch_normal(d3 , scope="genbn3")
    d3 = tf.nn.relu(d3)

    d3 = conv_cond_concat(d3 , yb)

    d4 = de_conv(d3 , weights2['wc3'] , biases2['bc3'] , out_shape=[batch_size , output_size , output_size , 1])

    return tf.nn.sigmoid(d4)


def sample_net(batch_size , z , y, output_size):

    yb = tf.reshape(y, shape=[batch_size, 1, 1, y_dim])


    z = tf.concat([z, y], 1)


    c1, c2 = int(output_size / 4), int(output_size / 2)
    print(c1)
    print(c2)

    # 10 stand for the num of labels
    d1 = fully_connect(z, weights2['wd'], biases2['bd'])
    d1 = batch_normal(d1, scope="genbn1" , reuse=True)
    d1 = tf.nn.relu(d1)

    d1 = tf.concat([d1, y], 1)

    d2 = fully_connect(d1, weights2['wc1'], biases2['bc1'])
    d2 = batch_normal(d2, scope="genbn2" , reuse=True)

    d2 = tf.nn.relu(d2)
    d2 = tf.reshape(d2, [batch_size, c1, c1, 64 * 2])

    d2 = conv_cond_concat(d2, yb)

    d3 = de_conv(d2, weights2['wc2'], biases2['bc2'], out_shape=[batch_size, c2, c2, 128])
    d3 = batch_normal(d3, scope="genbn3" , reuse=True)
    d3 = tf.nn.relu(d3)

    d3 = conv_cond_concat(d3, yb)

    d4 = de_conv(d3, weights2['wc3'], biases2['bc3'], out_shape=[batch_size, output_size, output_size, 1])

    return tf.nn.sigmoid(d4)


######### discriminent_net

weights = {

    'wc1': tf.Variable(tf.random_normal([5 , 5 , 11 , 10], stddev=0.02) , name='dis_w1'),
    'wc2': tf.Variable(tf.random_normal([5 , 5 , 20 , 64], stddev=0.02) , name='dis_w2'),
    'wc3' : tf.Variable(tf.random_normal([64*7*7 + y_dim , 1024] , stddev=0.02) , name='dis_w3') ,
    'wd' : tf.Variable(tf.random_normal([1024 + y_dim , channel] , stddev=0.02) , name='dis_w4')
}

biases = {

    'bc1': tf.Variable(tf.zeros([10]) , name = 'dis_b1') ,
    'bc2': tf.Variable(tf.zeros([64]) , name = 'dis_b2'),
    'bc3' : tf.Variable(tf.zeros([1024]) ,name =  'dis_b3') ,
    'bd' : tf.Variable(tf.zeros([channel]) ,name= 'dis_b4')

}

def dis_net(data_array , y , weights , biases , reuse=False):

    # mnist data's shape is (28 , 28 , 1)

    yb = tf.reshape(y , shape=[batch_size, 1 , 1 , y_dim])

    # concat
    data_array = conv_cond_concat(data_array , yb)

    conv1 = conv2d(data_array , weights['wc1'] , biases['bc1'])

    tf.add_to_collection('weight_1', weights['wc1'])
    conv1 = lrelu(conv1)
    conv1 = conv_cond_concat(conv1 , yb)

    tf.add_to_collection('ac_1' , conv1)

    conv2 = conv2d(conv1 , weights['wc2']  , biases['bc2'])
    conv2 = batch_normal(conv2 , scope="dis_bn1" , reuse=reuse)
    conv2 = lrelu(conv2)

    tf.add_to_collection('weight_2', weights['wc2'])

    tf.add_to_collection('ac_2', conv2)

    conv2 = tf.reshape(conv2 , [batch_size , -1])

    conv2 = tf.concat([conv2 , y] , 1)

    f1 = fully_connect(conv2 , weights['wc3'] , biases['bc3'])
    f1 = batch_normal(f1 , scope="dis_bn2" , reuse=reuse)
    f1 = lrelu(f1)
    f1 = tf.concat([f1 , y] , 1)

    out = fully_connect(f1 , weights['wd'] , biases['bd'])

    return tf.nn.sigmoid(out) , out
