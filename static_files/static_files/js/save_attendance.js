function depend(s1,s2)
{
    var sec1 = document.getElementById(s1).selectedIndex;
    var sec12 = document.getElementsByTagName("option")[sec1];

    var sec2 = document.getElementById(s2);

    sec2.innerHTML = "";

    /*if(sec12.id=="test3")
    {
        var opt = ["one|FY","two|SY","three|TY"];
    }
    if(sec12.id == "test2")
    {
        var opt=["one|FY","two|SY"];
    }
    if(sec12.id=="test1")
    {
        var opt = ["one|FY"];
    }*/
    var opt = sec12.id.split(",")

    for(var i in opt)
    {
        //var sp = opt[i].split("|");
        var new1 = document.createElement("option");
        //new1.value = sp[0];

        new1.value = opt[i].replaceAll("'", "");
        //new1.innerHTML = sp[1];
        new1.innerHTML = opt[i].replaceAll("'", "")
        sec2.options.add(new1);
    }
}


function sorting1(s) {

  var f_two=document.getElementById("check");
  f_two.value="hello";

  var s_index = document.getElementById(s).selectedIndex;
  var s_index_tag = document.getElementById(s).children[s_index];

  var table_tr = document.getElementsByTagName("tr");
  var table_tr=Array.from(table_tr);


  var time_mar = document.getElementById(s)[s_index].value;
  var id=time_mar.split(";")[0];
  document.getElementById("batch_id").value=id;


  var time = time_mar.split(";")[1];

  var start_time = time.split("-")[0];
  var start_minute = parseInt(start_time.split(":")[1]);
  var start_second = parseInt(start_time.split(":")[2]);
  var start_hour = parseInt(start_time.split(":")[0]);


  var end_time = time.split("-")[1];
  var end_minute = parseInt(end_time.split(":")[1]);
  var end_second = parseInt(end_time.split(":")[2]);
  var end_hour = parseInt(end_time.split(":")[0]);

   var h_tag_ele=document.getElementById("custume_head");
  var bold=s_index_tag.innerText;
  h_tag=`<p id="h">Batch:<b>${bold}</b> Time:<b>${time}<b></p>`;
  h_tag_ele.innerHTML=h_tag;

  var attendance_record = attendance_list[s_index-1];
 document.getElementById("attain_record").value=`(${attendance_record})`;

  var batch_ticked_list = attendance_record;

    for(var i in table_tr)
  {
  if(i!=0)
  {
     console.log(table_tr[i]);
      table_tr[i].style.display="none";
  }
  }


  for(var i in table_tr)
  {
    if (i != 0) {

      var col_time = table_tr[i].querySelector("td:nth-child(5)").innerHTML;
      var table_tag_id=table_tr[i].querySelector("td:nth-child(1)");

      var table_minute = parseInt(col_time.split(":")[1]);
      var table_second = parseInt(col_time.split(":")[2]);
      var table_hour = parseInt(col_time.split(":")[0]);
 console.log(start_hour, start_minute, end_hour, end_minute);
 console.log(table_hour, table_minute);


      if (table_hour >= start_hour && table_hour <= end_hour) {
          if(table_hour==start_hour)
          {
              if(table_minute>=start_minute)
              {
                  table_tr[i].style.display="";
              }
          }


          if(table_hour==end_hour)
          {
              if(table_minute<=end_minute)
              {
                  table_tr[i].style.display="";
              }
          }
     if (table_hour >  start_hour && table_hour < end_hour)
     table_tr[i].style.display="";
        }
      }
    }

    for(var i in table_tr)
    {
        if (i != 0) {

        var col1=table_tr[i].querySelector("td:nth-child(1)");
        var col1_checked=col1.querySelector("input[type='checkbox']");
            var col1_tagid = parseInt(col1.innerText);
            col1_checked.checked=false;
            console.log(batch_ticked_list);
            for(var k=0;k<batch_ticked_list.length;k++ )
            {
               if(col1_tagid==batch_ticked_list[k])
               {
               col1_checked.checked=true;
               }
            }
        }
    }

  }

var f_one=document.getElementById("form1");
var f2_two=document.getElementById("check");

f_one.addEventListener("submit",function(e){
console.log(f2_two.value);
if(f2_two.value!="hello")
{
e.preventDefault();
$("#exampleModalCenter").modal('show');
}
});

