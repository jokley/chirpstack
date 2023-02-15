function decodeUplink(input) {
     
    var port = input.fPort;
    var bytes = input.bytes;
    
    var data = {};
  
    var tmp = (bytes[0]<<8 | bytes[1]);
    var hum = (bytes[2]<<8 | bytes[3]);
    var battery = (bytes[4]<<8 | bytes[5]);
    
    data.temperature = (tmp)/100,
    data.humidity = (hum)/100,
    data.battery = battery
  
    
     return {
        data: data,
      }
    }