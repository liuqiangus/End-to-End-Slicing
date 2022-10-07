package com.example.offloadsocket;
/* energy & accuracy test*/

import android.os.Bundle;
import android.os.Environment;
import android.support.design.widget.TextInputEditText;
import android.support.v7.app.AppCompatActivity;

import java.io.BufferedReader;
import java.io.File;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.InputStreamReader;
import java.net.InetAddress;
import java.net.Socket;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.util.Log;
import android.widget.Button;
import android.view.View;
import android.widget.EditText;
import android.widget.TextView;

import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.TimeUnit ;
import com.loopj.android.http.*;

import cz.msebera.android.httpclient.Header;


public class SocketImageClient extends AppCompatActivity {

    int count = 0;
    private Socket socket;
    private static int SERVER_PORT = 9001;
    private static String SERVER_IP = "192.168.17.11";
    private static final String TAG = "TheImageMsg"; // filter
    private static String TheUrl = "http://"+ SERVER_IP + ":" + Integer.toString(SERVER_PORT+1000) + "/";
    private static List<Double> ThePerf = new ArrayList<Double>();
    private static List<Double> SendCount = new ArrayList<Double>();
    private static List<Double> SynSendCount = Collections.synchronizedList(SendCount);
    private static List<Double> SynThePerf = Collections.synchronizedList(ThePerf);
    private static HashMap<String, Long> TheMap = new HashMap<String, Long>();
    private static Map<String, Long> SynTheMap = Collections.synchronizedMap(TheMap);

    private double arrival_rate = 1.0;
    private Random randomno = new Random();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_socket_image_client);
    }


    public void TCP(View view){
        // start the connection thread
        Thread Conn_Thread = new Thread(conn);
        Conn_Thread.start();
        // start the recv thread
        Thread Recv_Thread = new Thread(recv);
        Recv_Thread.start();
        // start performance report thread
        Thread Http_Thread = new Thread(https);
        Http_Thread.start();

    }



    protected double getWaitTime(double lambda) {
        // the randomon should be global, otherwise reseted everytime
        return  Math.log(1-randomno.nextDouble())/(-lambda); // return in second
    }
//    public void EXIT(View view){
//        finish();
//        System.exit(0);
//        int pid = android.os.Process.myPid();
//        android.os.Process.killProcess(pid);
//    }

    protected Bitmap getImages(String path){
        File mfile = new File(path);
        if (mfile.exists()) {
            Bitmap bitmap = BitmapFactory.decodeFile(path);
            // Log.i(TAG, "Read image: " + path);
            return bitmap;
        } else {
            // Log.i(TAG, "Path not exist!");
            return null;
        }
    }

    private double calculateAverage(List <Double> TheList) {
        double sum = 0.0;
        synchronized (TheList) {
            if (!TheList.isEmpty()) {
                for (double element : TheList) {
                    sum += element;
                }
                return sum / TheList.size();
            }
        }
        return sum;
    }

    private String convert2string(List <Double> TheList) {
        DecimalFormat decimal_format = new DecimalFormat("#.##");
        StringBuilder strs = new StringBuilder();
        synchronized (TheList) {
            if (!TheList.isEmpty()) {
                for (double element : TheList) {
                    strs.append(decimal_format.format(element)+" "); // space between these data
                }
                return strs.toString();
            }
        }
        return strs.toString();
    }

    Runnable https = new Runnable() {
        @Override
        public void run() {
            TextView theresultview = (TextView) findViewById(R.id.TheResultView);
            DecimalFormat decimal_format = new DecimalFormat("#.##");
            String perf_strs;
            while (true) {
                SyncHttpClient syncHttpClient = new SyncHttpClient();
                RequestParams requestParams = new RequestParams();
                perf_strs = convert2string(SynThePerf); // calculate the average performance
                double avg = calculateAverage(SynThePerf); // calculate the average performance
                synchronized (SynThePerf){
                    SynThePerf.clear(); // clear the performance list
                }

                requestParams.add("perf", perf_strs);

                theresultview.setText("Traffic   :  " + decimal_format.format(arrival_rate) + "\nLatency :  " + decimal_format.format(avg));

                syncHttpClient.post(TheUrl, requestParams, new AsyncHttpResponseHandler() {
                    @Override
                    public void onSuccess(int statusCode, Header[] headers, byte[] responseBody) {
                        String response = new String(responseBody); // this is your response string
                        double traffic = Double.parseDouble(response);
                        arrival_rate = traffic;
                        Log.i("recv traffic is :", Double.toString(traffic));
                    }

                    @Override
                    public void onFailure(int statusCode, Header[] headers, byte[] responseBody, Throwable error) {
                        // Here you write code if there's error
                    }
                });

                // sleep for 1 second to retry if above exception is detected
                try {
                    TimeUnit.SECONDS.sleep(1);
                } catch (InterruptedException e) {
//                    System.out.println("sleep 1 sec is interrupted");
                }
            }
        }
    };

    Runnable conn = new Runnable() {
        @Override
        public void run() {
            // get all information
            Button thebutton = (Button) findViewById(R.id.TheButton);
            thebutton.setClickable(false);
            thebutton.setTextColor(0xff888888); // gray color

            TextView thetextview = (TextView) findViewById(R.id.TheLatencyView);

            TextInputEditText theserveraddr = (TextInputEditText) findViewById(R.id.Input_Addr);
//            EditText Traffic = findViewById(R.id.Traffic);
//            arrival_rate = Double. parseDouble(Traffic.getText().toString());
            TextInputEditText theserverport = (TextInputEditText) findViewById(R.id.Input_Port);
            SERVER_IP = theserveraddr.getText().toString();
            SERVER_PORT = Integer.parseInt(theserverport.getText().toString());
            TheUrl = "http://"+ SERVER_IP + ":" + Integer.toString(SERVER_PORT+1000) + "/";

            TextInputEditText theimagelocation = (TextInputEditText) findViewById(R.id.ImageLocation);

            String path = Environment.getExternalStorageDirectory() + theimagelocation.getText().toString();

            DataOutputStream dataOS2 = null;
            ByteArrayOutputStream baos = null;
            byte[] image_byte = new byte[0];

            File mfile = new File(path);
            String contents[] = mfile.list();

            while (true) {
                //  create a socket connection to the server
                try {
                    InetAddress serverAddr = InetAddress.getByName(SERVER_IP);

                    // Log.i(TAG, "New Socket");
                    socket = new Socket(serverAddr, SERVER_PORT);

                    // Log.i(TAG, "Setup ...");
                    dataOS2 = new DataOutputStream(socket.getOutputStream());

                } catch (Exception e) {
//                    e.printStackTrace();
                }

                //  send images continuously to the server

                while (true) {

                    try {
                        // Log.i(TAG, "Get bitmap");
                        Bitmap bitmap2 = getImages(path+contents[count%contents.length]);
                        baos = new ByteArrayOutputStream();
                        bitmap2.compress(Bitmap.CompressFormat.JPEG, 50, baos); // 50 quality
                        image_byte = baos.toByteArray();

                        dataOS2.writeInt(image_byte.length); // send len of data
                        Log.i(TAG, "image size is: " + image_byte.length);
                        dataOS2.writeInt(count);  // send id of packet
                        dataOS2.write(image_byte); // send the real data
                    } catch (Exception e)
                    {
//                        e.printStackTrace();
                        break;
                    }

                    thetextview.setText("Frame: " + Integer.toString(count) +", On-the-fly: " + Integer.toString((int)SynSendCount.size()));

                    // add the send time stamp for the image
                    synchronized (SynSendCount){
                        SynSendCount.add(1.0);
                    }

                    synchronized (SynTheMap){
                        SynTheMap.put(Integer.toString(count), System.currentTimeMillis());
                    }


                    while (SynSendCount.size()>arrival_rate)
                    {
                        try {
                            TimeUnit.MILLISECONDS.sleep(10);
                        } catch (InterruptedException e) {
                            e.printStackTrace();
                        }
                    }
                    // OTHERWISE, USE THIS TO HAVE PPP arrival rate
//                    try {
//                        // max wait time is 1 second incase too long wait and interference every action taken
//                        int wait_time = Math.max(Math.min((int)(getWaitTime(arrival_rate) *1000), 1000),100);// todo limited to [1fps, 10fps]for the RAN sys capability
//                        TimeUnit.MILLISECONDS.sleep(wait_time);
//                        // Log.i(TAG, "wait time is: " + wait_time);
////                        TimeUnit.MILLISECONDS.sleep((int)(1000/arrival_rate));
//                    } catch (InterruptedException e) {
////                        System.out.println("sleep 1 sec is interrupted");
//                    }
                    count += 1;
                }

                // sleep for 1 second to retry if above exception is detected
                try {
                    TimeUnit.SECONDS.sleep(1);
                } catch (InterruptedException e) {
//                    System.out.println("sleep 1 sec is interrupted");
                }
            }
        }
    };

    /* Define the Thread */
    Runnable recv = new Runnable() {

        @Override
        public void run() {

            Button thebutton = (Button) findViewById(R.id.TheButton);

            while (true) {
                BufferedReader br = null;
                try {
                    br = new BufferedReader(new InputStreamReader(socket.getInputStream()));
                } catch (Exception e) {
//                    e.printStackTrace();
                    continue;
                }

                double latency = 0.0;
                long send_time = 0L;
                long recv_time = 0L;
                int recv_id = 0;

                while (true) {

                    // Log.i(TAG, "receiving the next frame result...");
                    String rp = null;
                    try {
                        rp = br.readLine() ; //+ System.getProperty("line.separator")
                        String pkt_id = br.readLine();
                        recv_id = Integer.parseInt(pkt_id);
                        // Log.i(TAG, "Response recv id: " + Integer.toString(recv_id));
                    } catch (Exception e) {
//                        e.printStackTrace();
                        break;
                    }

                    // Log.i(TAG, "Response:" + rp);
                    synchronized (SynTheMap) {
                        String pkt_id = "";
                        if (SynTheMap.containsKey(Integer.toString(recv_id))) {
                            pkt_id = Integer.toString(recv_id);
                            send_time = SynTheMap.get(pkt_id);
                            recv_time = System.currentTimeMillis();
                            latency = recv_time - send_time; // in second
                            SynTheMap.remove(pkt_id); // remove the first one
                        }
                        else {
                            // Log.i(TAG, "########## not contain key:" + pkt_id);
                        }
                    }

                    // add the send time stamp for the image
                    synchronized (SynSendCount){
                        if (SynSendCount.size()>=1) {
                            SynSendCount.remove(0); // remove the first element
                        }
                    }

//                    // Log.i(TAG, "send_time:" + Long.toString(send_time));
//                    // Log.i(TAG, "recv_time:" + Long.toString(recv_time));

                    synchronized (SynThePerf) {
                        SynThePerf.add((double)latency);
                    }
                    // Log.i(TAG, "latency: " + Double.toString(latency));

                    try {
                        thebutton.setText("Offloading");
                    }catch (Exception e)
                    {
//                        e.printStackTrace();
                    }
                }
            }
        }
    };


}
