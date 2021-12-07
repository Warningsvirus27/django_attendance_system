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

  //var attendance_list = [];  rendering it from html page

  for(var i in table_tr)
  {
      if(table_tr[i].style.display=="none")
      {
        table_tr[i].style.display="";
      }
  }

  var time_mar = document.getElementById(s)[s_index].value;
  var id=time_mar.split(";")[0];
  var time_mar = time_mar.split(";")[1];


  // ----------------------------------------------- for h4 tag
   if(document.getElementById("h"))
   {
  document.getElementById("h").remove();
   }

  var h_tag_ele=document.getElementById("custume_head");
  var bold=s_index_tag.innerText;

  h_tag=`<p id="h">Batch:<b>${bold}</b> Time:<b>${time_mar}<b></p>`;
  var heading=1;
  h_tag_ele.insertAdjacentHTML("beforebegin",h_tag);
  // ----------------------------------------------
  document.getElementById("batch_id").value=id;
  var start_time = time_mar.split("-")[0];

  var start_minute = parseInt(start_time.split(":")[1]);
  var start_second = parseInt(start_time.split(":")[2]);
  var start_hour = parseInt(start_time.split(":")[0]);

  var end_time = time_mar.split("-")[1];

  var end_minute = parseInt(end_time.split(":")[1]);
  var end_second = parseInt(end_time.split(":")[2]);
  var end_hour = parseInt(end_time.split(":")[0]);

console.log(start_time);
console.log(end_time);

  var attendance_record = attendance_list[s_index-1];
  document.getElementById("attain_record").value=`(${attendance_record})`;

  var hidden = attendance_record;

  for(var i in table_tr)
  {
    if (i != 0) {

      var col = table_tr[i].querySelector("td:nth-child(5)").innerHTML;
      var col1=table_tr[i].querySelector("td:nth-child(1)");

      var col1_checked=col1.querySelector("input[type='checkbox']");

      var table_minute = parseInt(col.split(":")[1]);
      var table_second = parseInt(col.split(":")[2]);
      var table_hour = parseInt(col.split(":")[0]);

console.log(table_hour, table_minute, table_second);

    var show_list = false;

      if (table_hour >= start_hour && table_hour <= end_hour) {

        if (true)//(table_minute >= start_minute && table_minute <= end_minute)
        {
        // ---------------------------------------------------

        var col1_tagid = parseInt(col1.innerText);
         col1_checked.checked=false;
           for(var k=0;k<hidden.length;k++ )
           {
               if(col1_tagid==hidden[k])
               {
               col1_checked.checked=true;
               }
           }
           // -------------------------------------------------------
        }
        else {
          if(col1_checked.checked==true)
         { col1_checked.checked=false };
          table_tr[i].style.display="none";
        }
      } else {

      if(col1_checked.checked==true)
         { col1_checked.checked=false };
        table_tr[i].style.display="none";
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

